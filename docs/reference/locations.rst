=====================
Countries and regions
=====================

People write their location in their GitHub profile as they like: ``Berlin, Germany``, ``Lyon``, ``Portland, OR`` or ``the internet``. Contributor Community Insights finds the country of a location, for the query variable ``country``, for grouping, and for the tag of Horizon Europe.

How the country is found
========================

The location is split at commas, slashes, semicolons, ``|``, ``·``, parentheses, and at a dash or the word ``and`` between spaces: ``Berlin - Germany``, ``Berlin and Lisbon``. The parts are tried from the last to the first; the first part that is known gives the country. A part is known as:

- the name of a country in `GeoNames <https://www.geonames.org/>`_ (through `geonamescache <https://github.com/yaph/geonamescache>`_), or a common other name such as ``USA``, ``UK``, ``England``, ``Deutschland`` or ``Türkiye``;
- a two-letter country code in capitals, such as ``DE``; after a city, a code of a US state is the state: "Portland, OR";
- the name of a US state;
- the name of a city with more than 15 000 people, also in other languages written in Latin letters. When cities share a name, the biggest one is taken: "Paris" is in France, "Cambridge, MA" is in the US because of the state.

Case and accents do not matter: ``zurich`` is ``Zürich``. Locations that are none of these, such as ``Remote`` or ``Earth``, have no country. A location can be wrong or old; the country is a guess from what people wrote.

Horizon Europe
==============

`Horizon Europe <https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe_en>`_ is the research programme of the European Union. In **GitHub access → Profile**, check *Show a Horizon Europe tag* to see a tag next to the locations in its countries, on the contributors page and on the page of a person. The query variable ``horizon_europe`` is ``True`` for these people: ``horizon_europe and prs_merged >= 1``.

The countries are the member states of the EU and the associated countries, from the `list of participating countries of the European Commission <https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/list-3rd-country-participation_horizon-euratom_en.pdf>`_ (January 1, 2026) and the later associations it announced:

Member states of the EU
    Austria, Belgium, Bulgaria, Croatia, Cyprus, Czechia, Denmark, Estonia, Finland, France, Germany, Greece, Hungary, Ireland, Italy, Latvia, Lithuania, Luxembourg, Malta, Netherlands, Poland, Portugal, Romania, Slovakia, Slovenia, Spain, Sweden.

Associated countries
    Albania, Armenia, Bosnia and Herzegovina, Canada (Pillar II), Egypt, the Faroe Islands, Georgia, Iceland, Israel, Japan (Pillar II, since July 2026), Kosovo, Moldova, Montenegro, New Zealand (Pillar II), North Macedonia, Norway, Republic of Korea (Pillar II), Serbia, Switzerland, Tunisia, Türkiye, Ukraine, United Kingdom.

Some countries take part only in Pillar II, "Global Challenges and European Industrial Competitiveness"; the tag does not tell the parts apart. The list is in ``community_insights/locations/horizon.py``; please `report <https://github.com/PyCalendar/community-insights/issues>`_ when it changes.
