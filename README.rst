Flonda is an experimental tool to publish pure Python code as conda packages

Installation::

    pip install flonda

Usage:

First, create `Flit <http://flit.readthedocs.io/en/latest/>`__ metadata for your
module or package. Then

.. code-block:: shell

    # Build conda packages (with flit.ini in CWD)
    flonda build

    # Set up anaconda.org client
    conda install anaconda-client
    anaconda login

    # Publish packages to anaconda.org
    flonda publish

But you probably shouldn't use this yet. It's *highly experimental*, and you
risk building broken packages.
