==============================
Create the GitHub OAuth app
==============================

People can sign up with an email address and add :doc:`tokens <tokens>`, so an OAuth app is optional. With one, people can also sign in with GitHub and link their account, which is then used as their first token. Register it once:

#. Open https://github.com/settings/developers and choose **New OAuth App**.
#. Set the **Homepage URL** to the address of your installation, such as ``https://community.example.org`` or ``http://localhost:5000`` for a try-out.
#. Set the **Authorization callback URL** to that address plus ``/accounts/github/login/callback/``, for example ``http://localhost:5000/accounts/github/login/callback/``.
#. Create the app, generate a client secret and put both values in the environment: ``GITHUB_CLIENT_ID`` and ``GITHUB_SECRET`` (see :doc:`../reference/configuration`).

Access to private repositories
==============================

The sign-in asks GitHub only for ``read:user``. Somebody who wants to read private repositories presses **Allow reading private repositories** on the page *GitHub access*, and GitHub asks them for the ``repo`` permission. It allows more than reading; the site only reads. ``GITHUB_SCOPE`` changes what is asked at sign in for everybody.
