# -*- coding: utf-8 -*-
{
    'name': 'iKrux Login',
    'version': '19.0.1.0.0',
    'category': 'Hidden/Tools',
    'author': 'iKrux',
    'website': 'https://www.ikrux.com',
    'summary': 'iKrux-branded, split-screen login page',
    'description': """
iKrux Login
===========

Rebrands the sign-in screen in iKrux colours: a navy brand panel carrying the
white iKrux logo and tagline beside a clean sign-in card.

The restyle is made on web.login_layout, the shell shared by the login,
sign-up, reset-password and two-factor pages, so all of them take the new look.
The login form itself is left as Odoo builds it and only restyled in CSS, so
the fields, buttons and hooks that auth_signup, auth_totp and auth_passkey add
to it keep working unchanged.

The palette is taken from ikrux.com - teal #40978A, green #66C28F and navy
#091124 - and is set once, at the top of static/src/scss/login.scss. Every
rule there is scoped to the login body class, so the portal and the backend
are untouched.
""",
    'depends': ['web'],
    'data': [
        'views/login_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'ikrux_login/static/src/scss/login.scss',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
