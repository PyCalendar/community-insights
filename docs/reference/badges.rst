=======
Badges
=======

``/badge/<token>.svg`` returns a badge for the response time of a project. The token is secret and belongs to the project, so the address of a private project cannot be guessed. A badge reads the database only; it never calls GitHub and never uses a token. Update the data with **Read from GitHub**.

.. list-table::
   :header-rows: 1

   * - Parameter
     - Default
     - Meaning
   * - ``kind``
     - ``pr``
     - ``pr`` or ``issue``
   * - ``percentile``
     - ``50``
     - 0 to 100: the time within which that share of first responses came
   * - ``class``
     - any
     - the name of a class of people; without it the first response of anyone counts
   * - ``model``
     - ``measured``
     - ``measured``, ``normal``, ``exponential`` or ``kaplan-meier``: how the percentile is computed, see :doc:`../explanation/response-times`. *Kaplan-Meier* also counts the items without a response and says *not reached* when that share never got one.
   * - ``label``
     - made from the others
     - the text of the left side, such as ``response time``; at most 60 characters

Example, the 95th percentile of the first response of collaborators to pull requests:

.. code-block:: markdown

    ![PR response](https://community.example.org/badge/TOKEN.svg?kind=pr&percentile=95&class=collaborator%20or%20higher)

Without data the badge says *no data*. An unknown class gives a 404.

The badge builder on the overview of a project shows the code of the badge for **Markdown**, **reStructuredText**, **HTML** and the plain **Link**, each with a **Copy** button. The code links the badge to the overview, so people who open it see where the number comes from:

.. code-block:: rst

    .. image:: https://community.example.org/badge/TOKEN.svg?kind=pr&percentile=95
       :alt: pull request response time
       :target: https://community.example.org/s/plone~volto/

Share a chart
=============

Every chart has **Share this chart** under it. The page that opens shows the chart with its code in the same four formats, linked to the page the chart was on, with its time range and query. A chart reads the database only, like a badge. Everything shared opens without a sign in: a project is shared as its public repositories, such as ``/s/plone~volto+plone~plone.restapi/`` for ``/s/3/``, and the address keeps the time range, the query and your classes of people (``classes``), so others see the same numbers. A project without a public repository stays private: only you see it after you sign in, and the page says so. **Share** at the top of a statistics page copies the address of the page in the same way.
