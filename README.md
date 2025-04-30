# pausanias

Digital humanities tools for manipulating the text of Ἑλλάδος Περιήγησις

# Tooling

All the programs use Python. Lots of digital humanities folks run into
trouble with environments and dependencies, so I've made sure
everything works nicely with `uv`. Download `uv` from here:
https://github.com/astral-sh/uv (it's one command, so it's quick, and
it won't disrupt any other installation you might have).

The first time you run a `uv` command it will output something like this:

```
Using CPython 3.11.6 interpreter at: /Users/gregb/anaconda3/bin/python3.11
Creating virtual environment at: .venv
```



# Data Loading

`uv run pausanias_importer.py description_of_greece.txt`

This should respond with 

```
Successfully imported 3170 passages into pausanias.sqlite
```

