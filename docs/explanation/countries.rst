=====================================
Countries and languages of the people
=====================================

The page **Countries** shows on a map of the world where the contributors of a project are from, and the page **Languages** estimates which languages they speak. Both read the location that people write in their GitHub profile. This page explains how a location becomes a country, a place on the map and a set of languages, and where these guesses go wrong.

Where the data comes from
=========================

GitHub profiles have a field *Location*: free text, written by the person, often empty. It can be *Berlin*, *Berlin, Germany*, *Cardiff, Wales*, *Remote*, *Earth* or a joke. Nothing checks it. The site reads it with the name and the avatar of each person who contributed (see :ref:`contributions`), and reads it again after some days.

The contributors of the pages are those of the time range at the top: everybody, not a bot, who opened an issue or a pull request, commented or reviewed in it. *3/4 contributors mapped* means that 3 of the 4 contributors of the time range have a location whose country is known. The others have no location, were not read yet, or wrote something that names no known country; the page lists the latter with their location.

From a location to a country and a place
========================================

The site first looks the location up offline, in the place names of `GeoNames <https://www.geonames.org/>`_ (through the Python package ``geonamescache``):

#. The location is split at commas, semicolons, slashes, vertical bars, brackets, a dash between spaces, and the word *and*.
#. The parts are read from the last to the first, as people write *City, Country*. The first part that is a country decides the country: its name in English, a common other name (*USA*, *UK*, *Deutschland*, *Holland*), or its two-letter code (*DE*). A two-letter code after a city is a state of the United States if there is one (*Portland, OR*). A state of the United States is the United States.
#. A part that names a region with languages of its own, such as *Wales* or *Catalunya*, gives the region and its country (see :ref:`regions`).
#. A part that is a city, of at least 15 000 people, gives the place: the biggest city of that name in the country found, or the biggest of that name anywhere if no country is named. *Paris* is in France, *Paris, Texas* in the United States. A city in another country than the one named is left out: *Lyon, Germany* is Germany without a place.
#. The region of a city is that of GeoNames: Cardiff is in Wales, Barcelona in Catalonia.

When GeoNames finds no country, or finds the country but not the place of a location that names more than a country (a village and its country), the site asks `Nominatim <https://nominatim.org/>`_, the search of OpenStreetMap, which knows villages and addresses. Its answer is used if it is in the same country as GeoNames found, or if GeoNames found nothing. A place of Nominatim is a dot on the map if it is a city, a town, a village or a smaller place; a whole country or state is no dot.

Each location is found once and kept in the database, also when nothing was found, so it is not asked again. A person who changes their location gets the new one found. Only the fetch of a repository asks Nominatim, at most once a second and at most 100 times a fetch (``NOMINATIM_PER_FETCH``, see :doc:`../reference/configuration`), as the usage policy of OpenStreetMap asks; pages never ask it. Until a fetch has found a location, the pages use what GeoNames finds. An installation can switch Nominatim off with an empty ``NOMINATIM_URL``.

The map
=======

The map is drawn from the countries of `Natural Earth <https://www.naturalearthdata.com/>`_ (public domain, scale 1:50 million), in the Equal Earth projection, which keeps the areas of the countries: a big country is not drawn bigger than it is. Antarctica is left out. ``make world-map`` makes the map again (``scripts/world_map.py``).

- **Colours.** Black is a country without contributors. With contributors, a country is green: dark green for one contributor, light green for the country with the most, and in between on a logarithmic scale. With 100 contributors from one country, a country with 10 is halfway, so one big country does not leave all others nearly as dark as one contributor. White lines of 2 pixels separate the countries at every zoom.
- **The box below the map.** It always has the same size and place. Pointing at a country shows *3 contributors from Germany*, or that nobody is from there; pointing at a city shows the city below its country, such as *Berlin: 2 contributors*. Without anything pointed at, it shows the country chosen, and without that how to use the map. The border of the country pointed at is three times as wide: 6 pixels instead of 2.
- **Small countries.** Luxembourg, Malta or Singapore are a few pixels or less. A country smaller than about 12 square pixels at the current zoom is small: it gets a dot at its centre, and the pointer chooses it within 10 pixels of that centre, also on top of a bigger neighbour. Zoomed in, it becomes big enough to point at itself.
- **Clicks.** A click on a country or a city opens ``#country=XX`` with the code of the country, which shows the country below the map: its contributors and their locations, the first and the last contribution from there, and its official languages. The country is outlined, and the box keeps its text. The address can be shared.
- **Cities.** Contributors with a clear city or place are a green circle with a white border, one per place. Its area grows in proportion to the contributors there: the radius grows with the square root of their number, 3 pixels for one, 6 for four, at every zoom. Only the cities of contributors are on the map. Pointing at a city shows it in the box; a click chooses its country.
- **Zoom.** The mouse wheel or a pinch zooms, dragging moves the map, and the buttons zoom in, out, and back to the whole world.

.. _languages:

Languages
=========

Nobody is asked what they speak. The page **Languages** estimates it from the countries:

- A contributor counts for each **official language** of their country: those that are official in law, or in fact (*de facto official*), in the data of `CLDR <https://cldr.unicode.org/>`_, the Unicode Common Locale Data Repository, through the Python package Babel. Austria counts for German, like Germany; Switzerland for German, Swiss German, French and Italian; Belgium for Dutch, French and German.
- A contributor in a **region with languages of its own** counts for those instead (see :ref:`regions`): Wales for English and Welsh.
- The languages are ranked by these contributors, and each lists the countries they come from. A contributor can count for several languages, so the shares add up to more than 100 %.
- **Likely speakers** adds up, for each contributor with a known country, the share of the people of that country who speak the language after CLDR, official or not. 64 % of the people in Germany speak English after CLDR, so 10 contributors from Germany add 6.4 likely speakers of English. This counts languages that are spoken widely without being official, such as English in most of Europe.

Both are estimates for groups, not facts about a person. A contributor from Switzerland may speak only French; a contributor from Germany may not speak German at all.

.. _regions:

Regions with languages of their own
-----------------------------------

CLDR knows which languages are official in a part of a country only (``official_regional``), not in which part. For the regions that people write often, the site has its own table (``community_insights/locations/regions.py``), after the articles of Wikipedia on these regions and their languages:

.. list-table::
   :header-rows: 1

   * - region
     - names it knows
     - languages
   * - Wales, United Kingdom
     - ``Wales``, ``Cymru``
     - English, Welsh
   * - Scotland, United Kingdom
     - ``Scotland``, ``Alba``
     - English, Gaelic
   * - Northern Ireland, United Kingdom
     - ``Northern Ireland``
     - English, Irish
   * - Catalonia, Spain
     - ``Catalonia``, ``Catalunya``
     - Spanish, Catalan
   * - Basque Country, Spain
     - ``Basque Country``, ``Euskadi``
     - Spanish, Basque
   * - Galicia, Spain
     - ``Galicia``
     - Spanish, Galician
   * - Valencia region, Spain
     - ``Valencian Community``, ``Comunitat Valenciana``
     - Spanish, Catalan
   * - Balearic Islands, Spain
     - ``Balearic Islands``, ``Illes Balears``
     - Spanish, Catalan
   * - Quebec, Canada
     - ``Quebec``
     - French
   * - Friesland, Netherlands
     - ``Friesland``, ``Fryslan``
     - Dutch, Frisian
   * - South Tyrol, Italy
     - ``South Tyrol``, ``Sudtirol``, ``Alto Adige``
     - Italian, German

A city in one of these regions counts for it too: *Cardiff* is in Wales.

Packages that were looked at
----------------------------

No package was found that knows the official languages of both countries and their regions. Babel ships CLDR with the languages of each country, their status and the share of speakers, and is used. ``pycountry`` and ``iso3166-2`` know the regions of countries (ISO 3166-2), but not their languages. Wikidata knows the official languages of regions (property P37), but asking it needs the network or a large download. A Python package of its own for the table of regions would be small; it is kept in this project until another one needs it.

Where the guesses go wrong
==========================

- Many people write no location, or *Remote*, *Earth* or *the internet*: they are not mapped.
- A location is what a person chose to write: where they live, were born, or would like to be.
- Names that many places share go to the biggest one (*Cambridge* is in the United Kingdom; *Cambridge, MA* in the United States).
- A location that names several countries (*Berlin and Lisbon*) counts for the last one known.
- Nominatim finds the most likely place for a text; for short or unusual texts, that can be wrong.
- Borders and names of countries follow Natural Earth and CLDR; they are not a statement of the project.
