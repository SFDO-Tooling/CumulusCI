import os

import click


@click.command()
@click.option("--prev", required=True, help="Previous version tag")
@click.option("--next", required=True, help="Next version tag")
def main(prev, next):
    os.system("git fetch")
    cmd = (
        'gh api --method POST -H "Accept: application/vnd.github.v3+json" '
        + "/repos/SFDO-Tooling/CumulusCI/releases/generate-notes"
        + f" -f tag_name='{next}' "
        + "-f target_commitish='main' "
        + f"-f previous_tag_name='{prev}' --jq .body "
        + "| pandoc -f gfm -t rst"
    )
    print(cmd)
    os.system(cmd)


if __name__ == "__main__":
    main()
