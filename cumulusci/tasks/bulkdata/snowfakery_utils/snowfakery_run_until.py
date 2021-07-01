import typing as T

from cumulusci.core import exceptions as exc


class RunUntilBase:
    # subclasses need to fill in these two fields
    sobject_name: str = None
    target: int = None
    gap: int = None

    def set_target_and_gap(
        self, sobject_name: T.Optional[str], num_as_str: T.Union[str, int]
    ):
        self.sobject_name = sobject_name
        try:
            self.target = self.gap = int(num_as_str)
        except (TypeError, ValueError):
            raise exc.TaskOptionsError(f"{num_as_str} is not a number")

    def split_pair(self, param):
        parts = param.split(":")
        if len(parts) != 2:
            raise exc.TaskOptionsError(
                f"{param} is in the wrong format for {self.option_name}"
            )
        return parts

    @property
    def nothing_to_do(self):
        return self.gap <= 0


class RunUntilRecipeRepeated(RunUntilBase):
    option_name = "--run-until-recipe-repeated"
    nothing_to_do_because = "You asked for zero repetitions."

    def __init__(self, sf, param):
        self.set_target_and_gap(None, param)


class RunUntilRecordsLoaded(RunUntilBase):
    option_name = "--run-until-records-loaded"
    nothing_to_do_because = "You asked for zero records."

    def __init__(self, sf, param):
        parts = self.split_pair(param)
        self.set_target_and_gap(*parts)


class RunUntilRecordInOrg(RunUntilRecordsLoaded):
    option_name = "--run-until-records-in-org"

    def __init__(self, sf, param):
        parts = self.split_pair(param)
        self.set_target_and_gap(*parts)
        query = f"select count(Id) from {self.sobject_name}"
        # TODO: fall back to other APIs
        self.in_org_count = sf.query(query)["records"][0]["expr0"]
        gap = self.target - int(self.in_org_count)
        self.gap = max(gap, 0)

    @property
    def nothing_to_do_because(self):
        return f"The org has {self.in_org_count} {self.sobject_name} records. You asked for {self.target}"


COUNT_STRATEGIES = {
    "run_until_recipe_repeated": RunUntilRecipeRepeated,
    "run_until_records_loaded": RunUntilRecordsLoaded,
    "run_until_records_in_org": RunUntilRecordInOrg,
}


def determine_run_until(options, sf):
    selected_strategies = [
        (strategy, options.get(strategy))
        for strategy in COUNT_STRATEGIES.keys()
        if options.get(strategy)
    ]

    if len(selected_strategies) > 1:
        raise exc.TaskOptionsError(
            "Please select only one of " + ", ".join(COUNT_STRATEGIES.keys())
        )
    elif not selected_strategies:
        strategy_choice = ("run_until_recipe_repeated", "1")
    else:
        strategy_choice = selected_strategies[0]

    strategy_name, param = strategy_choice
    strategy_impl = COUNT_STRATEGIES[strategy_name]

    return strategy_impl(sf, param)


class PortionGenerator:
    """
    Logic to generate batch sizes and know when we are done.

    Calling class must manage sets_created_so_far because it may
    have information unknown to this class, e.g. failures,
    processes running on other nodes, etc.
    """

    def __init__(
        self,
        target: int,
        min_batch_size: int,
        max_batch_size: int,
        start_count: int = 0,
    ):
        self.target = target
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.next_batch_size = min_batch_size

    def done(self, sets_created_so_far):
        return self.gap(sets_created_so_far) <= 0

    def gap(self, sets_created_so_far):
        return self.target - sets_created_so_far

    def next_batch(self, sets_created_so_far: int):
        """Batch size starts at min_batch_size and grows toward max_batch_size
        unless the count gets there first

        The reason we grow is to try to engage the org's loader queue earlier
        than we would if we waited for the first big batch to be generated.
        """
        self.sets_created = sets_created_so_far
        # don't generate more records than needed to reach our target
        # or current batch size
        # or the max batch size
        self.batch_size = min(
            self.gap(sets_created_so_far), self.next_batch_size, self.max_batch_size
        )
        # don't generate fewer than zero
        self.batch_size = max(self.batch_size, 0)
        self.next_batch_size = int(self.next_batch_size * 1.1)
        return self.batch_size
