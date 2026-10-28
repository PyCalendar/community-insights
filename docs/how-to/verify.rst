===========================
Check the numbers yourself
===========================

Every statistics page has **Data and sources** with the tables behind the numbers. Download ``responses`` as CSV or Parquet; :doc:`../reference/downloads` lists its columns. Its ``seconds_<class>`` columns are the seconds until the first response of each class of people, empty where there was none.

Compute the fits
================

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

With Parquet, the numbers and times keep their types. Read the table and what it is, such as the repositories and the time range:

.. code-block:: python

    import json
    import pandas
    import pyarrow.parquet

    table = pandas.read_parquet("responses-1.parquet")
    about = json.loads(pyarrow.parquet.read_schema("responses-1.parquet").metadata[b"community-insights"])

The times are seconds; the page shows them as ``3h 12min``.

The badges use the measured percentile, ``numpy.percentile(x, p)``, unless their parameter ``model`` names another statistic; without a class, of ``seconds_any``.

Count the items without a response
==================================

Items nobody answered yet are not in ``x`` above, so the times look shorter than they are. The row *Kaplan-Meier* of the overview counts them as waiting at least as long as they were observed (until they were closed, or until the download), with lifelines:

.. code-block:: python

    import lifelines

    column = table["seconds_bot"]
    durations = column.fillna(table["observed_seconds"])
    fitted = lifelines.KaplanMeierFitter().fit(durations, event_observed=column.notna())
    # the median: the first time at which at most half are still waiting
    fitted.median_survival_time_
    # the curve of the overview, with its confidence interval
    fitted.survival_function_, fitted.confidence_interval_survival_function_

scipy gives the same median with ``scipy.stats.ecdf(scipy.stats.CensoredData(uncensored=column.dropna(), right=table.loc[column.isna(), "observed_seconds"])).sf``.

If less than half of the items got a response, the median is not reached: the page shows ``-``.

Compute the trend
=================

The trend under the tables of the overview is a straight line through the logarithm of the time until the first response of anybody, over the day each item was opened (:ref:`trend`):

.. code-block:: python

    import numpy
    import statsmodels.api as sm

    answered = table.dropna(subset=["seconds_any"])
    days = (pandas.to_datetime(answered["created_at"]) - pandas.to_datetime(answered["created_at"]).min()).dt.total_seconds() / 86400
    fitted = sm.OLS(numpy.log1p(answered["seconds_any"]), sm.add_constant(days)).fit()
    # percent per month, and the p-value
    (numpy.exp(fitted.params.iloc[1] * 30.44) - 1) * 100, fitted.pvalues.iloc[1]
