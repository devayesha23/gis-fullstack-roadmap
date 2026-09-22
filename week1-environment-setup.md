# Setting Up a GIS Development Environment: A Beginner Friendly Walkthrough (With All the Errors I Actually Hit)

As a GIS engineer, I like keeping my local environment clean and rebuilding it properly whenever I start a new phase of work. This time, I decided to document the whole process, step by step, on Windows, without WSL, including every error I ran into along the way.

This article walks through exactly what I did, in the order I did it. I am sharing the errors on purpose. If you are setting up a similar environment, you will probably hit some of these same errors too, and it helps to know they are normal, not a sign that you are doing something wrong.

## Why I Am Writing This

Most tutorials online skip the messy parts. They show you the happy path, install this, run that, done. In reality, almost nothing works perfectly on the first try, especially on Windows. I wanted to write something that shows the real process, mistakes included, so it actually helps someone follow along without getting stuck wondering if they did something wrong.

## Part 1: Setting Up Python and the Geospatial Stack

### Why I Started Here

Before touching any spatial data, you need a Python environment that can actually handle geospatial work. The two libraries that matter most here are GeoPandas, which lets you work with spatial data the same way you would work with a normal spreadsheet in Python, and Shapely, which handles the actual geometry math behind the scenes, points, lines, polygons, distances.

### Installing Miniconda

On Windows, installing these geospatial libraries directly with pip often causes problems, because they depend on some tricky underlying software called GDAL. Conda handles this dependency mess far better than pip does. So I installed Miniconda first.

I created a dedicated environment just for this project, so it would not interfere with anything else on my system:

```
conda create -n gis-refresh python=3.11
conda activate gis-refresh
```

Then I installed the core packages:

```
conda install -c conda-forge geopandas shapely pandas jupyter sqlalchemy psycopg2 -y
```

### Error One: GeoPandas Would Not Import

After installing everything, I tried to check it worked:

```
python -c "import geopandas; print(geopandas.__version__)"
```

And got this:

```
ModuleNotFoundError: No module named 'geopandas'
```

A little frustrating, since the install had seemed to go fine. The fix turned out to be simple. I checked whether I was actually inside the right environment:

```
conda env list
```

Turns out the first install had not fully completed. Running the install command again, properly inside the activated environment, fixed it.

**What I learned:** always double check which environment is active before installing anything. It is an easy thing to overlook, especially when you are juggling multiple terminals.

### Error Two: Jupyter Was Not Recognized

Once GeoPandas was working, I tried launching Jupyter to test everything visually:

```
jupyter notebook
```

And got:

```
'jupyter' is not recognized as an internal or external command
```

Turns out Jupyter itself had never actually installed, even though I thought it was part of the original install command. Fixed it directly:

```
conda install -c conda-forge jupyter -y
```

### The First Real Test

Once Jupyter opened, I ran a small script to confirm everything was actually working together, not just installed:

```python
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

df = pd.DataFrame({
    'name': ['Islamabad', 'Lahore', 'Karachi'],
    'lat': [33.6844, 31.5497, 24.8607],
    'lon': [73.0479, 74.3436, 67.0011]
})

gdf = gpd.GeoDataFrame(
    df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326"
)

print(gdf)
gdf.plot()
```

Seeing three little dots appear on a tiny plot, roughly where Islamabad, Lahore, and Karachi actually sit, was a nice confirmation that pandas, GeoPandas, Shapely, and plotting were all genuinely working together, not just individually installed.

## Part 2: Setting Up PostgreSQL and PostGIS

### Why a Spatial Database

Regular databases store text, numbers, and dates. A spatial database can also store shapes, points, lines, polygons, and answer questions like "which of these points falls inside this boundary." PostgreSQL is a free, open source database, and PostGIS is the extension that adds spatial abilities to it. This combination shows up constantly in real GIS work, so it made sense to set it up properly from the start.

### Installing PostgreSQL and PostGIS

I downloaded PostgreSQL from the official site, ran the installer with default settings, and set a password for the postgres user, the account that manages everything. Then I used a tool called Stack Builder, which comes with the installer, to add PostGIS.

### Error Three: psql Not Recognized

After installing, I tried checking the version:

```
psql --version
```

And got the classic "not recognized as an internal or external command" error. This meant Windows did not know where to find the Postgres tools.

I went looking for the actual installed folder, and realized the folder name did not match what I expected. I had assumed it would be named after the full version number, like 18.6, but it was actually just named 18. Small mismatch, but it meant the path I added to my system's PATH setting was wrong.

Once I corrected the path to match the real folder name, and made sure to open a brand new terminal window afterward, since PATH changes do not apply to already open windows, it worked.

**What I learned:** never guess a folder name. Always check File Explorer to see what it is actually called before configuring anything around it.

### Creating the Database

Once psql worked, creating the database and enabling PostGIS was smooth:

```sql
CREATE DATABASE gis_refresh;
\c gis_refresh
CREATE EXTENSION postgis;
SELECT PostGIS_Version();
```

Seeing a real PostGIS version number print back was a satisfying confirmation that the spatial extension was genuinely active.

### A Quick Test Table

```sql
CREATE TABLE test_points (id serial PRIMARY KEY, geom geometry(Point, 4326));
INSERT INTO test_points (geom) VALUES (ST_MakePoint(73.0479, 33.6844));
SELECT * FROM test_points;
```

One row came back with real spatial data in it. Small win, but it meant the whole chain, install, extension, table, insert, query, was working end to end.

### Error Four: DBeaver Would Not Show My Database

I installed DBeaver next, a free tool that lets you browse databases visually instead of typing raw SQL constantly. I connected it to Postgres, but my new gis_refresh database was nowhere to be found, only the default postgres database showed up.

Turns out DBeaver, by default, only displays the one database you originally connected with. The fix was going into the connection settings and turning on an option called "Show all databases." Once I did that and refreshed, gis_refresh appeared right where it should have been all along.

## Part 3: QGIS and Understanding Coordinate Systems

### Why QGIS Matters

QGIS is a free desktop application for viewing and working with spatial data visually. Even for someone doing most of their real work through code, QGIS is genuinely useful for quickly checking whether data looks right before trusting it in a script. It is also something most GIS job interviews assume you are comfortable with.

### Loading a Dataset

I downloaded a free dataset from Natural Earth, a country boundaries shapefile, and loaded it into QGIS. Seeing a full world map appear, made of individual country shapes, is always a satisfying first step.

### Reprojecting: A Good Reminder About EPSG Codes

Every spatial dataset uses something called a coordinate reference system, or CRS, which is basically the rulebook for how coordinates translate to real locations on Earth. The dataset started in a CRS called WGS84, which uses degrees of latitude and longitude, the same system GPS uses.

I wanted to reproject it into a different system called Web Mercator, the one Google Maps and most web maps use. While exporting, QGIS asked me to pick the target CRS by its code, and I typed 3257 by mistake instead of 3857. One digit off, and it took me to a completely unrelated coordinate system.

**What I learned:** EPSG codes are just numbers, and a single typo silently takes you somewhere completely different, with no warning. Always double check the code before confirming.

Once I fixed the typo and actually switched the project's display to EPSG:3857, I could finally see the real effect of the reprojection. Antarctica, which is smaller than Africa in real life, suddenly looked like a giant band stretching across the entire bottom of the map. That is the famous distortion problem with Mercator projections, they preserve angles nicely for navigation, but badly distort size the farther you get from the equator. Genuinely one of those things that is more fun to see for yourself than to just read about.

### The Buffer Operation, and Two Silly Mistakes

A buffer creates a zone of a certain distance around a shape, like drawing a 500 kilometer ring around every country. This is a real operation used constantly in actual GIS work, things like "find every hospital within 10 kilometers of this area."

Since the map was now displaying in meters, not degrees, I needed to enter the buffer distance in meters too. I typed what I thought was 500,000, meaning 500 kilometers.

The result covered the entire screen in one solid color. Something was very wrong.

Turns out I had accidentally typed several extra zeros, turning 500,000 meters into something like 500,000,000 meters, roughly 25 times the actual size of Earth. No wonder it looked like one giant block.

I fixed it, tried again, and made the exact same mistake a second time, a different miscount of zeros. On the third attempt, I slowed down, typed the number one digit at a time, and counted the digits before running the tool. That time it worked correctly, small 500 kilometer halos around each country, exactly as expected.

**What I learned:** when entering large numbers into any tool, slow down and actually count the digits before confirming. It feels almost too simple to mention, but this exact mistake is incredibly easy to make and easy to miss.

### Selecting Countries by Attribute

The last exercise was filtering the data to show only certain countries, in this case, only countries in Asia, using a simple expression:

```
"CONTINENT" = 'Asia'
```

This selected 47 countries, and exporting just those gave a clean map of Asia alone. This kind of filtering is the same basic logic you would use later with a SQL WHERE clause or a GeoPandas filter, just done visually here instead of in code.

## Part 4: Git and GitHub

### Why This Matters

Git tracks every change made to your work over time. GitHub hosts that history online, so it becomes visible, backed up, and shareable. This is baseline expectation for any development role, and it is also a great way to build a visible, dated record of ongoing work.

### Getting Connected

I installed Git, set my name and email so commits would be properly labeled, and created a personal access token on GitHub, since plain password login is no longer allowed for security reasons.

I created a new public repository, cloned it down to my computer, and started adding my work.

### One Small Mixup

While organizing files, I accidentally ended up with a strangely named file, a notebook and an article had somehow merged into one file with a broken name. A simple rename and reorganizing the files properly into two separate files fixed it. A small reminder that keeping file names and folders organized early on saves confusion later.

## Wrapping Up

By the end of this process, I had a solid, working local environment. Python with GeoPandas and Jupyter, a PostgreSQL database with PostGIS enabled, QGIS for visual work, and a live GitHub repository tracking all of it.

None of this was smooth on the first try. Real errors showed up nearly every single day, wrong PATH entries, mistyped numbers, mismatched file names, a wrong EPSG code. But every single one had a clear, findable reason once I stopped and looked closely, rather than just guessing and retrying blindly.

If you are setting up something similar, I hope seeing these exact mistakes helps you recognize them faster if they happen to you too.

## Frequently Asked Questions

### Why does GeoPandas fail to import even after installing it?

Usually because the wrong environment is active, or the install did not fully finish the first time. Check which environment is active, then check what is actually installed inside it.

### Why does psql say it is not recognized after installing PostgreSQL?

Almost always a PATH problem. Check the actual folder name PostgreSQL installed into, since it might not match the full version number you expected, and always open a new terminal window after changing PATH settings.

### Why does my database not show up in DBeaver even though I created it?

DBeaver only displays the database you originally connected with, by default. Turn on "Show all databases" in the connection settings to see everything on the server.

### Why did my buffer cover the entire map?

Most likely an extra zero or two typed into the distance field by accident. Always double check large numbers digit by digit before running a geoprocessing tool.

### Do I need to memorize EPSG codes?

No, but always double check them before confirming a reprojection. A single wrong digit takes you to a completely different, unrelated coordinate system with no warning.
