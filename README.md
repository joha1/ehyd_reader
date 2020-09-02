# ehyd_reader

`ehyd_reader` provides a Python script to read in hydro(geo)logic data obtained from the Austrian [ehyd](https://ehyd.gv.at/) platform.
It turns the ehyd csv files into a dictionary, pandas dataframe or a csv file that's easier to read with other software.

To use it, download `ehyd_reader.py`, put it into your working directory, `from ehyd_reader import ehyd_reader` and read in csv files for groundwater levels, river stages, precipitation or spring flows with `data = ehyd_reader('filename.csv', output_type='df')`.

## A more detailed explanation



## Examples

Jupyter notebooks containing some working examples on what you can do with `ehyd_reader` and how to do it are available in the [examples](https://github.com/joha1/ehyd_reader/tree/master/examples) folder.

## Dependencies

`ehyd_reader` needs [pandas](https://github.com/pandas-dev/pandas) to work. It also uses the [haversine distance from scikit learn](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.haversine_distances.html). The latter could be removed, if getting the distance a measurement station has been moved over its livetime is not important.

