"""A module to show styling.

Run from the command line with:

    $ python3 -m watchgha.demo

"""

import rich.console

from .sample_data import sample

if __name__ == "__main__":
    console = rich.console.Console(highlight=False)
    sample(outfn=console.print)
