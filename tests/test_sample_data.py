import io

from textwrap import dedent

from watchgha.sample_data import sample


def test_sample_data():
        stream = io.StringIO()
        sample(outfn=lambda s: print(s, file=stream))

        expected = dedent("""\
            [white bold]fix: most awesome fix[/] nedbat/test \\[push]   [dim]4b2ff5812479  @04:55pm[/]
               [default]↻ in_progress [/] [white bold]Test suite      [/]   [blue link=https://github.com/owner/repo/actions/runs/123456789]view 123456789[/]
                  A delayed job                  [dim]⏲[/] [dim]queued[/]
                  A failed job                   [red bold]✗[/] [red bold]failure Didn't work[/]
                  A finished job                 [green bold]✓[/] [green bold]success[/]
                  Test suite Py 3.8              [default]↻[/] [green]•[/][green]•[/][green]•[/][default]◦[/][white]•[/][dim white]•[/][dim white]•[/][default] Run the tests[/]
                  Test suite Py 3.9              [default]↻[/] [green]•[/][green]•[/][default]◦[/][white]•[/][dim white]•[/][dim white]•[/][dim white]•[/][default] Prep tests[/]
                  Test suite Py 3.10             [default]↻[/] [green]•[/][green]•[/][green]•[/][default]◦[/][white]•[/][dim white]•[/][dim white]•[/][default] Run the tests[/]
                  Test suite Py 3.11             [default]↻[/] [green]•[/][green]•[/][default]◦[/][white]•[/][dim white]•[/][dim white]•[/][dim white]•[/][default] Prep tests[/]
               [default]↻ in_progress [/] [white bold]Malicious  data[/]   [blue link=https://github.com/owner/repo/actions/runs/123456789]view 123456789[/]
                  A [1mMALICIOUS[0m job        [dim]⏲[/] [dim]queued[/]
               [green bold]✓ success     [/] [white bold]A success run   [/]   [blue link=https://github.com/owner/repo/actions/runs/123456789]view 123456789[/]
               [red bold]✗ startup_failure[/] [white bold]A startup_failure run[/]   [blue link=https://github.com/owner/repo/actions/runs/123456789]view 123456789[/]
                  Just one job                   [dim]⏲[/] [dim]queued[/]
               [default]⏭ skipped     [/] [white bold]A skipped run   [/]   [blue link=https://github.com/owner/repo/actions/runs/123456789]view 123456789[/]
               [red bold]✗ failure     [/] [white bold]A failure run   [/]   [blue link=https://github.com/owner/repo/actions/runs/123456789]view 123456789[/]
                  Just one job                   [dim]⏲[/] [dim]queued[/]
               [default]† cancelled   [/] [white bold]A cancelled run [/]   [blue link=https://github.com/owner/repo/actions/runs/123456789]view 123456789[/]
                  Just one job                   [dim]⏲[/] [dim]queued[/]
            """)
        assert stream.getvalue() == expected
