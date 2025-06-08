import geopandas as gpd


taz = gpd.read_file(r"W:\TAZ ShapeFile V3.2\TAZ ShapeFile V32.shp")
print(taz.head())