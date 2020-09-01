# ehyd_reader

`ehyd_reader` provides a Python script to read in hydro(geo)logic data obtained from the Austrian [ehyd](https://ehyd.gv.at/) platform.
It turns the ehyd csv files into a dictionary, pandas dataframe or a csv file that's easier to read with other software.

To use it, download `ehyd_reader.py`, put it into your working directory, `from ehyd_reader import ehyd_reader` and read in csv files for groundwater levels, river stages, precipitation or spring flows with `data = ehyd_reader('filename.csv', output='df')`.

