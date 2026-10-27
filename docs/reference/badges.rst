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

Example, the 95th percentile of the first response of collaborators to pull requests:

.. code-block:: markdown

    ![PR response](https://community.example.org/badge/TOKEN.svg?kind=pr&percentile=95&class=collaborator%20or%20higher)

Without data the badge says *no data*. An unknown class gives a 404.
