import json
import re

from cumulusci.core.utils import parse_datetime, process_bool_arg
from cumulusci.tasks.base_source_control_task import BaseSourceControlTask
from cumulusci.vcs.models import AbstractRepo


class ReleaseReport(BaseSourceControlTask):
    task_options = {  # TODO: should use `class Options instead`
        "date_start": {
            "description": "Filter out releases created before this date (YYYY-MM-DD)"
        },
        "date_end": {
            "description": "Filter out releases created after this date (YYYY-MM-DD)"
        },
        "include_beta": {
            "description": "Include beta releases in report [default=False]"
        },
        "print": {"description": "Print info to screen as JSON [default=False]"},
    }
    DATE_FORMAT = "%Y-%m-%d"

    def _init_options(self, kwargs):
        super(ReleaseReport, self)._init_options(kwargs)
        self.options["date_start"] = (
            parse_datetime(self.options["date_start"], self.DATE_FORMAT)
            if "date_start" in self.options
            else None
        )
        self.options["date_end"] = (
            parse_datetime(self.options["date_end"], self.DATE_FORMAT)
            if "date_end" in self.options
            else None
        )
        self.options["include_beta"] = process_bool_arg(
            self.options.get("include_beta", False)
        )
        self.options["print"] = process_bool_arg(self.options.get("print", False))

    def _run_task(self):
        releases = []
        repo: AbstractRepo = self.get_repo()
        regex_compiled_prefix = re.compile(
            r"^((?P<sandbox>{})|(?P<production>{}))(?P<remaining>.*)$".format(
                self.project_config.project__git__push_prefix_sandbox,
                self.project_config.project__git__push_prefix_production,
            )
        )
        regex_compiled_date = re.compile(r"\s*(?P<date>\d\d\d\d-\d\d-\d\d)")
        for release in repo.releases():
            if release.prerelease and not self.options["include_beta"]:
                continue
            if (
                self.options["date_start"]
                and release.created_at < self.options["date_start"]
            ):
                continue
            if (
                self.options["date_end"]
                and release.created_at > self.options["date_end"]
            ):
                continue
            release_info = {
                "url": release.html_url,
                "name": release.name,
                "tag": release.tag_name,
                "beta": release.prerelease,
                "time_created": release.created_at,
                "time_push_sandbox": None,
                "time_push_production": None,
            }
            release_body = release.body or ""
            for line in release_body.splitlines():
                m = regex_compiled_prefix.match(line)
                if m:
                    if not m.group("remaining"):
                        self.logger.warning(
                            "[%s] Nothing found after push date prefix: %s",
                            release_info["url"],
                            line,
                        )
                        continue
                    m2 = regex_compiled_date.match(m.group("remaining"))
                    if not m2:
                        self.logger.warning(
                            (
                                "[%s] Could not find date in line: %s\n"
                                "Use the format YYYY-MM-DD"
                            ),
                            release_info["url"],
                            line,
                        )
                        continue
                    if m.group("sandbox"):
                        key = "time_push_sandbox"
                    else:
                        key = "time_push_production"
                    release_info[key] = parse_datetime(
                        m2.group("date"), self.DATE_FORMAT
                    )
            releases.append(release_info)
        self.return_values = {"releases": releases}
        if self.options["print"]:
            print(json.dumps(releases, indent=4, sort_keys=True, default=str))
