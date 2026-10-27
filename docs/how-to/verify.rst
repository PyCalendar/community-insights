===========================
Check the numbers yourself
===========================

Every statistics page has **Data and sources** with the tables behind the numbers, as CSV or JSON:

``responses``
    one row per pull request or issue: ``seconds_any`` until the first response of anybody, ``seconds_<class>`` until the first response of each class of people (empty if there was none), ``responded``, and ``observed_seconds``, how long it waited until it was closed or until the download. Items without a response are *censored* data.

``items``
    pull requests and issues: author, state, merged, times.

``events``
    every comment, review and opening, with actor and time.

``contributors``
    the contributors table.

The fits of the overview are made with scipy. This reproduces them for the class *bot*:

.. code-block:: python

    import numpy
    import pandas
    import scipy.stats

    table = pandas.read_csv("responses-1.csv")
    x = table["seconds_bot"].dropna().to_numpy()

    # measured
    x.mean(), scipy.stats.sem(x), numpy.median(x), numpy.percentile(x, 95)

    # normal (maximum likelihood)
    mu, sigma = scipy.stats.norm.fit(x)
    mu, sigma / len(x) ** 0.5, scipy.stats.norm.ppf(0.95, mu, sigma)

    # exponential
    loc, scale = scipy.stats.expon.fit(x, floc=0)
    scale, scale / len(x) ** 0.5, scipy.stats.expon.median(scale=scale), scipy.stats.expon.ppf(0.95, scale=scale)

The times are seconds; the page shows them as ``3h 12min``.

The badges use the measured percentile, ``numpy.percentile(x, p)``; without a class, of ``seconds_any``.

Censored data
=============

Items nobody answered yet are not in ``x`` above, so the times look shorter than they are. The row *Kaplan-Meier* of the overview counts them as waiting at least as long as they were observed (until they were closed, or until the download), with scipy:

.. code-block:: python

    column = table["seconds_bot"]
    data = scipy.stats.CensoredData(
        uncensored=column.dropna(),
        right=table.loc[column.isna(), "observed_seconds"],
    )
    sf = scipy.stats.ecdf(data).sf
    # the median: the first time at which at most half are still waiting
    sf.quantiles[sf.probabilities <= 0.5][0]

If less than half of the items got a response, the median is not reached: the page shows ``-``.
