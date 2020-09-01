#coding=UTF-8


def ehyd_reader(filename, output_type, write_csv='False',
                  interpolate='False'):
    """
    Reads in a CSV file containing a hydrologic time series (filename).
    Meant to be used with files obtained from ehyd.gv.at, taking into
    account the intricacies of this data (ISO 8859-15 file, use of
    german Umlauts, using the term "Lücke" for NaN, decimal comma).
    Use 'dict' or 'df' to specify wether you want a dict or dataframe as
    output.
    If you want a "proper" CSV file in your working directory, use
    "write_csv=True".
    Set interpolate to 'True' if you want to interpolate over missing
    data. For small gaps, this should be OK, but if 'DataError'
    indicates a lot of missing data, this is probably going to cause
    issues when further handling the data.
    """

    # Import the needed modules.
    import pandas as pd
    import numpy as np
    import os
    from sklearn.metrics.pairwise import haversine_distances
    from math import radians
    # The last two imports are needed to figure out how much the station moved
    # over its lifetime. If that's not needed, the whole stuff around the 
    # variable "StationMove" can be removed.

    # A lot of metadata start with ';' and end with a newline.
    # Lets define a little function for that.
    def splitter(tester):
        start_str = tester.find(';')+1
        end_str = tester.find('\n')
        t_str = tester[start_str:end_str]
        return t_str

    # define a long-ish function to read the coordinates,
    # needed twice, later
    def coord_calculator(RawCoords):
        nonlocal MetaError
        Coordstring = str(RawCoords)
        Longitudestart = Coordstring.find(';')+1
        Longitudeend = Coordstring.rfind(';')-1
        Latitudestart = Coordstring.rfind(';')+1
        Latitudeend = Coordstring.find('\n')
        raw_Longitude = Coordstring[Longitudestart:Longitudeend]
        raw_Latitude = Coordstring[Latitudestart:Latitudeend]
        # Remove trailing whitespace.
        stripped_Lon = raw_Longitude.rstrip()
        stripped_Lat = raw_Latitude.rstrip()
        # There can be cases where Lat and Lon are missing i.e. meaning they're
        # set to 0. If that's the case, all the stuff below fails. so we gotta
        # test for that.
        if stripped_Lat == '0':
            Lat = np.nan
            Lon = np.nan
            print('Station', HZB, 'is missing coordinates!')
            MetaError = 'Missing_coords'
        else:
            # Grab the parts and turn them into floats
            sDeg_Lon = stripped_Lon[0:2]
            Deg_Lon = float(sDeg_Lon)
            sMin_Lon = stripped_Lon[3:5]
            Min_Lon = float(sMin_Lon)
            sSec_Lon = stripped_Lon[6:8]
            Sec_Lon = float(sSec_Lon)
            sDeg_Lat = stripped_Lat[0:2]
            Deg_Lat = float(sDeg_Lat)
            sMin_Lat = stripped_Lat[3:5]
            Min_Lat = float(sMin_Lat)
            sSec_Lat = stripped_Lat[6:8]
            Sec_Lat = float(sSec_Lat)
            # Put it all together
            Lon = Deg_Lon + (Min_Lon / 60) + (Sec_Lon / 3600)
            Lat = Deg_Lat + (Min_Lat / 60) + (Sec_Lat / 3600)
            Lon = round(Lon, 8)
            Lat = round(Lat, 8)
            # Should only result in 6 decimals,
            # but the division could result in a repeating decimal,
            # so let's keep that at a sane size.
        return Lat, Lon

    # since filename is kinda generic, change it to current_csv
    current_csv = filename

    f1 = open(current_csv, 'r', encoding='cp1252')
    table = f1.readlines(3000)
    # Reads in only 3000 characters/bytes. Most ehyd files appear to contain 
    # around 1500 characters in the metadata, so this has a good margin of 
    # error. Since readlines is quite fast, this limitation can also be
    # discarded without much of a penalty( ~100µs vs. 9ms for a 1MB file).
    f1.close()

    # Extract the name of the station:
    StationNameLine = table[0]
    StationName = splitter(StationNameLine)

    # Set metadata that might not be in every file to the 'NaN' string, to show
    # that they're not available.
    Province = 'NaN'
    CatchmentSize = 'NaN'
    CatchmentSymbol = 'NaN'
    StationMove = 'NaN'
    Subcatchment = 'NaN'
    RegName = 'NaN'
    # set depth to not available for things that do not have it
    depth = 'NaN'
    elev = 'NaN'

    # Grab various important information from the header and find the line in
    # which the data starts.
    # Will fail when a file is smaller than 40 lines, but such short time
    # series do not make sense to work with.
    # Will also fail if the headers of the csvs get bigger than 40 lines.
    # As of now, they're around 34, so 40 leaves a bit of a margin.
    # If it fails, increase header_counter as you see fit.
    # AS of now, this can only handle groundwater levels, river levels,
    # precipitation and spring flows. If it shall be extended to other types,
    # some logic is needed to distinguish between the different possibilities
    # that one of the current 'datatype' can contain. E.g. river temperature 
    # not only needs to search for 'Gew\xe4sser' as of now, but also for
    # 'WTemperatur'.
    # Thus, we set the datatype to NA at first, and change it only for files
    # that fit the rest of the Analysis:
    datatype = 'NA'
    MetaError = 'no_error'
    DataError = 'no_error'
    header_counter = 0
    while header_counter < 40:
        tester_list = table[header_counter]
        tester = str(tester_list)  # must be turned into a string,
        # otherwise we cant find strings in it.
        if 'Gew\xe4sser' in tester:
            datatype = 'Riverwater'
            CatchmentName = splitter(tester)
        if 'Niederschlag' in tester:
            datatype = 'Precipitation'
            CatchmentName = StationName
            # Catchment name is set to the name of the station.
        if 'Hauptquelle' in tester:
            datatype = 'Spring'
        if 'Grundwasser' in tester:
            datatype = 'Groundwater'
            CatchmentName = splitter(tester)
            # Gets the written name and short symbol for the catchment, e.g.
            # 'Grazer Feld (Graz/Andritz - Wildon) [MUR]'
            # the Murdurchbruchstal is missing the [MUR] marker.
            # So we have to deal with that too.
            if '[' in CatchmentName:
                NameEnd = CatchmentName.find(']')
                NameStart = NameEnd - 3
                CatchmentSymbol = CatchmentName[NameStart:NameEnd]
            else:
                CatchmentSymbol = 'NA'
            # Gets the short symbol for the catchment, such as
            # MUR, DRA (=Drau), DUJ (=Danube below Jochenstein) etc
            Groundwaterbody_name2 = table[header_counter - 1]
            # Normally there are two names for the groundwater body, the larger
            # 'Grundwasserkörper' and the subregion 'PorenGW-Gebiet' which can
            # be very local (few square km).
            Subcatchment = splitter(Groundwaterbody_name2)
        if 'Dienststelle' in tester:
            RegName = splitter(tester)
            # Who is responsible for the station. Mostly indicates which state.
            # E.g. 'HD-Steiermark'. Can overlap with 'Messstellenbetreiber' and
            # 'Bundesland', the latter being rare, however.
            # For Vienna and Lower Austria, it can also contain
            # 'HD-Wien (MA 45)' or 'Magistratsabteilung 31' with added clutter
            # or no indication of the state.
        # In this case there can also be a 'Bundesland' row:
        if 'Bundesland' in tester:
            Province = splitter(tester)
        # And to complicate matters further, there can also be a
        # 'Messstellenbetreiber', i.e. who operates (or owns?) the station:
        if 'Messstellenbetreiber' in tester:
            Operator = splitter(tester)
        if 'HZB-Nummer' in tester:
            # Keep the unique identifier used in ehyd
            HZB = int(splitter(tester))
            print('HZB:', HZB)
        if 'HD-Nummer' in tester:
            # Besides the HZB number, there's often also the HD number, used by
            # the state authorities. Often, this number is also included in the
            # name of the station. Can also contain letters and spaces, so
            # we'll leave that as a string.
            HD_num = splitter(tester)
        if 'DBMS-Nummer' in tester:
            # Some stations also have a DBMS number besides or instead of the
            # HD number. Seems like it's only numbers, but nothing known about
            # it, so lets keep it string.
            DBMS_num = splitter(tester)
        if 'Einzugsgebiet' in tester:
            # find the size of the catchment
            CatchmentSize = splitter(tester)
        if 'Koordinaten' in tester:
            # Sometimes a station gets moved and there will be all the
            # coordinates it ever had listed in the file. The lines below try
            # to find the last (=most current) coordinates by searching for the
            # term 'Exportzeitreihe' which comes after the last location.
            CoordTester = table[header_counter + 3]
            if 'Exportzeitreihe' in CoordTester:
                # This means there is only one row of Coordinates, so the
                # station didn't move.
                CoordValues = header_counter + 2
                CoordsChanged = 'False'
            else:
                # There's more than one row of Coordinates. We need to set the
                # first one as OldCoords to calculate the distance.
                print('Station got moved during its livetime.')
                CoordsChanged = 'True'
                MetaError = 'Station_moved'
                OldCoords = table[header_counter + 2]
                OldCoords = coord_calculator(OldCoords)
                CoordTester = table[header_counter + 4]
                if 'Exportzeitreihe' in CoordTester:
                    CoordValues = header_counter + 3
                else:
                    CoordTester = table[header_counter + 5]
                    if 'Exportzeitreihe' in CoordTester:
                        CoordValues = header_counter + 4
                    else:
                        CoordValues = header_counter + 5
                        print('Station', HZB, 'has been moved at least 4 times! \n',
                              'Coordinates might be of an older location, please check this station!')

            Coords = coord_calculator(table[CoordValues])
            Lat = Coords[0]
            Lon = Coords[1]
            if CoordsChanged == 'True':
                # Print info about how far the station got moved. Sometimes, 
                # coordinates are missing, so we need some routine to deal with
                # missing coordinates
                if MetaError == 'Missing_coords':
                    print('Station', HZB, 'was moved by an unknown distance! \n',
                          'Using the coordinates of the older location!')
                    Coords = OldCoords
                    Lat = Coords[0]
                    Lon = Coords[1]
                else:
                    # Uses the haversine distance from scikit learn. see
                    # https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.haversine_distances.html
                    # or
                    # https://en.wikipedia.org/wiki/Haversine_formula
                    # could probably also be implemented without scikit-learn.
                    # Needs to be turned into radians to work with.
                    Coords_rad = [radians(i) for i in Coords]
                    OldCoords_rad = [radians(i) for i in OldCoords]
                    StationMove = haversine_distances(
                        [Coords_rad, OldCoords_rad]) * 6371 * 1000
                    # Multiply with earth radius in meters to get the distance.
                    StationMove = round(StationMove[0, 1], 2)
                    # output is an array, this should get the distance without
                    # the rest, rounded to two decimals (=centimeters).
                    print('Sation', HZB, 'was moved by',
                          int(StationMove), 'meters.')

        if 'Messpunkthöhe:' in tester:
            elev = tester.replace(",", ".")
            elev = splitter(elev)
            elev = float(elev)
        if 'Sohllage' in tester:
            depth = tester.replace(",", ".")
            depth = splitter(depth)
            depth = float(depth)
        if 'Geländehöhe-Hauptquelle' in tester:
            # can be an elevation of a spring.
            # but is this really needed? What about Pegelnullpunk?
            elev = tester.replace(",", ".")
            elev = splitter(elev)
            if elev == '':
                elev = 'NaN'
            else:
                elev = float(elev)
        if 'Pegelnullpunkt' in tester and datatype == 'Riverwater':
            # This fails for precipitation, because they have the data 2 lines
            # below, whereas springs have it afterwards.
            elev = str(table[header_counter+2])
            elev = elev.replace(",", ".")
            elev = splitter(elev)
            if elev == '':
                elev = 'NaN'
            else:
                elev = float(elev)
        if 'Werte:' in tester:
            WerteStart = header_counter
            # Finds the line where the data starts
        header_counter += 1

    if depth != 'NaN':
        teufe = round((elev - depth), 2)
        # Due to how floating point numbers work, we sometimes run into values
        # like 11.799999999999983 where it should be 11.8 so lets round it to
        # take care of that.
    else:
        teufe = 'NaN'

    hydroTS = pd.read_csv(current_csv,
                          skiprows=WerteStart+1, decimal=',',  
                          sep='\s*\;\s*', usecols=[0, 1], index_col=0,
                          dayfirst=True, parse_dates=True, engine='python',
                          encoding='cp1252', names=['date', 'level'],
                          na_values='Lücke')

    # The data sometimes gets read as object, but we need float.
    hydroTS.level = hydroTS.level.astype(float)

    # Normalize the whole thing to get rid of hours and minutes.
    # If those are needed, the following line can be removed,
    # but it'll wreak havok with irregular times.
    hydroTS.index = hydroTS.index.normalize()

    # get the lowest and the largest date
    Min_date = hydroTS.index.min()
    Max_date = hydroTS.index.max()
    Mini_date1 = str(Min_date)
    Maxi_date1 = str(Max_date)
    Mini_date = Mini_date1[0:10]
    Maxi_date = Maxi_date1[0:10]
    # hardcoded to get rid of the hours and seconds.
    # Might fail if anything in the date format changes.

    Min_year = Min_date.year
    Max_year = Max_date.year
    data_years = Max_year - Min_year

    # Check if there is a gap in the index, which can cause issues with some 
    # further procsessing. First we need to find the frequency of the data.
    # We also need to get rid of the hours of the day, else days with multiple
    # measurements will wreak havoc.
    firstdate = hydroTS.index[0]
    seconddate = hydroTS.index[1]
    datedelta = seconddate - firstdate
    # Pandas timedelta. Seems like it defaults to days, but just to make sure:
    dayinterval1 = datedelta.days
    # Results in an int with the number of days between two days.
    # 1=daily timeseries; 28-31=monthly
    # However, some csv files can havechanging intervals. Let's do a few more
    # tests to find out, by probing the interval at the end and in the middle.
    lastdate = hydroTS.index[-1]
    slastdate = hydroTS.index[-2]
    datedelta = lastdate - slastdate
    dayinterval2 = datedelta.days
    middate = hydroTS.index[len(hydroTS.index)//2]
    smiddate = hydroTS.index[len(hydroTS.index)//2 - 1]
    datedelta = middate - smiddate
    dayinterval3 = datedelta.days

    if dayinterval1 == dayinterval2 == dayinterval3 == 1:
        TS_freq = 'D'
        #hydroTS = hydroTS.asfreq(TS_freq)

    elif min(dayinterval1, dayinterval2, dayinterval3) > 1:
        if min(dayinterval1, dayinterval2, dayinterval3) > 27:
            TS_freq = 'MS'
            #hydroTS = hydroTS.asfreq(TS_freq)
        else:
            TS_freq = 'MS'
            #hydroTS = hydroTS.asfreq(TS_freq)
            print('Station', HZB, 'has irregular measurement times! \n',
                  'Check the index before doing calculations on it.')
            DataError = 'Irregular_measure_times_M'

    else:
        TS_freq = 'D'
        #hydroTS = hydroTS.asfreq(TS_freq)
        print('Station', HZB, 'has irregular measurement times! \n',
              'Check the index before doing calculations on it.')
        DataError = 'Irregular_measure_times_D'
    # The commented out
    #hydroTS = hydroTS.asfreq(TS_freq)
    # lines can resample it to the frequency it apparently has.
    # Will pad missing dates and insert NaN as a value,
    # which will then be taken care of by the stuff below.

    # Built a empty date range with the same start, end and frequency as the
    # orignal data and get its length:
    testdates = pd.date_range(Mini_date, Maxi_date, freq=TS_freq)
    testlength = len(testdates)

    # Get the length of the real data and compare it. If it differs, there must
    # be a gap in the data.
    Rlength = len(hydroTS)
    # Counts everything, including NaN.
    lengthdifference = testlength - Rlength

    if lengthdifference != 0:
        hydroTS = hydroTS[~hydroTS.index.duplicated()]
        # Get rid of duplicate entries, keeping the first one. For data that 
        # has many measurements per day, this is not a good idea. ehyd data
        # should have only one per day, so this deals with some rare errors,
        # but for the raw data, this can be problematic.
        # the ~ is apparently a reversal of the booleans in that duplicated.
        # see
        # https://stackoverflow.com/questions/13035764/remove-rows-with-duplicate-indices-pandas-dataframe-and-timeseries
        print('Two measurements at one day. first measurement deleted')
        DataError = 'Doublemeasurement'
    if lengthdifference > 4:
        # Apparently, there is some issues around 1945 (war?) where total
        # months are missing, including dates. 
        DataError = 'Gapdata'
        print('there is a gap in the data')
        print('lengthdifference')
        print(lengthdifference)
    if data_years < 5:
        # Data that is too short can't reliably be used for many statistics.
        DataError = 'Shortdata'
        print('time series very short')
    if Min_year > 2010:
        DataError = 'Shortdata'
        print('time series very short')
    else:
        # count the NaNs:
        Rcount = hydroTS.level.count()  # counts only valid numbers
        NaN_Number = Rlength-Rcount
        NaN_Number = float(NaN_Number)
        Percent_Data = Rlength/100
        Ten_Percent = Percent_Data*10
        if NaN_Number > Ten_Percent:
            DataError = '10+percGap'
            print('10 percent of data missing')

        # Count how many NaNs there are following each other
        ConsNaNs = hydroTS.level.isna().astype(int).groupby(
                   hydroTS.level.notna().astype(int).cumsum()).sum().max()

        if TS_freq == 'D' and ConsNaNs > 14:
            DataError = '14+dayGap'
            print('more than 14 consecutive NaN in daily data')
        if TS_freq == 'MS' and ConsNaNs > 3:
            DataError = '3+monthsGap'
            print('more than 3 consecutive NaN in monthly data')

        if interpolate == 'True':
            # Get rid of the NaN in the dataset.
            # This is just a crude interpolation.
            # For data with just a few, this shouldn't be an issue, but if
            # DataError = '10+percGap', '3+monthsGap' or '14+dayGap'
            # this is probably not a valid approach.
            hydroTS.level = hydroTS.level.interpolate()

    if output_type == 'df' or write_csv == 'True':
        output_header = pd.MultiIndex.from_product(
            [[datatype], [StationName], [HZB], [HD_num],
             [DBMS_num], [CatchmentName], [CatchmentSymbol],
             [Subcatchment], [RegName], [Province], [Operator],
             [CatchmentSize], [Lat], [Lon], [StationMove],
             [elev], [depth], [teufe], [DataError], [MetaError]],
            names=['datatype', 'StationName', 'HZB', 'HD_num',
                   'DBMS_num', 'CatchmentName', 'CatchmentSymbol',
                   'Subcatchment', 'RegName', 'Province', 'Operator',
                   'CatchmentSize', 'Lat', 'Lon', 'StationMove',
                   'elev', 'depth', 'teufe', 'DataError', 'MetaError'])
        hydroTS.columns = output_header
        output = hydroTS
    if write_csv == 'True':
        filename_out = str('%s.csv' % (HZB))
        hydroTS.to_csv(filename_out, sep=';')

    if output_type == 'dict':
        output = {'DataError': DataError, 'MetaError': MetaError,
                  'StationName': StationName, 'CatchmentName': CatchmentName,
                  'CatchmentSymbol': CatchmentSymbol,
                  'Subcatchment': Subcatchment, 'RegName': RegName, 'HZB': HZB,
                  'HD_num': HD_num, 'DBMS_num': DBMS_num, 'Province': Province,
                  'Operator': Operator, 'CatchmentSize': CatchmentSize,
                  'Lat': Lat, 'Lon': Lon, 'elev': elev, 'depth': depth,
                  'teufe': teufe, 'StationMove': StationMove,
                  'datatype': datatype, 'timeseries': hydroTS}

    return output
