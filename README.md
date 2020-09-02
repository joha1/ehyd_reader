# ehyd_reader

`ehyd_reader` provides a Python script to read in hydro(geo)logic data obtained from the Austrian [ehyd](https://ehyd.gv.at/) platform.
It turns the ehyd csv files into a dictionary, pandas dataframe or a csv file that's easier to read with other software.

To use it, download `ehyd_reader.py`, put it into your working directory, `from ehyd_reader import ehyd_reader` and read in csv files for groundwater levels, river stages, precipitation or spring flows with `data = ehyd_reader('filename.csv', output_type='df')`.

## A more detailed explanation

The [Bundesministerium Landwirtschaft, Regionen und Tourismus (Austrian Federal Ministry of Agriculture, Regions and Tourism); BMLRT](https://www.bmlrt.gv.at/) provides access to almost 5000 hydrogeologic and hydrologic time series from all over Austria at the [https://ehyd.gv.at](https://ehyd.gv.at/) website.
These time series are provided as csv files. 
As such, it is trivial to open them with various software tools, such as libre Office, Microsoft Excel or to read them with various programming or scripting languages such as MATLAB, R or Python.

However, there are two issues with these csv files `ehyd_reader` aims to solve:

  * As ehyd is aimed at an Austrian audience, the files are written in German, so the metadata can be hard to decipher for people not speaking German. Further, the use of umlauts can make handling them complicated.
  * The files are using a somewhat uncommon way of formatting a csv, which makes (automated) handling of the files a hassle.
  
While all of these issues are easily solved when you want to open a file or two with the tool of your choice, it can become quite tedious when you're trying to work with a large number of files, especially since not every formatting quirk and error is contained in every file.
With `ehyd_reader` all of these issues should be solved, so that you can concentrate on working with the data, either continuing in python, or based on more conventionally formatted csv files or (using some more intermediate steps in python, see [examples](https://github.com/joha1/ehyd_reader/tree/master/examples)) based on other data exchange formats, such as hdf or excel.

However, two important limitations remain:
While [ehyd](https://ehyd.gv.at/) offers a great wealth of data over all of Austria, ranging back to the 19th century, it does not offer a clear license for the data, so the raw data can not be (re)shared.
Hence, all the examples start with a download of the data.
Further, this downloads have to happen by clicking around on the [ehyd](https://ehyd.gv.at/) website, or by grabbing specific wells with urlreader, since the [ehyd](https://ehyd.gv.at/) website does not offer an api for downloading the data.




## Examples

For some examples of what can be done based on `ehyd_reader`, check out [Haas and Birk (2019)](https://doi.org/10.1016/j.ejrh.2019.100597), looking at trends in Austrian groundwater levels.

For some more hands-on examples on how to use `ehyd_reader` for your own work, check out the Jupyter notebooks containing some working examples on what you can do with `ehyd_reader` and how to do it in the [examples](https://github.com/joha1/ehyd_reader/tree/master/examples) folder.

## Dependencies

`ehyd_reader` needs [pandas](https://github.com/pandas-dev/pandas) to work. It also uses the [haversine distance from scikit learn](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.haversine_distances.html). The latter could be removed, if getting the distance a measurement station has been moved over its livetime is not important.

