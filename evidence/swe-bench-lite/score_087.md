
#### Query: issue title

| repo | issues | Model D top-1 / 3 / 5 | Graphify top-1 / 3 / 5 |
|---|---|---|---|
| django/django | 114 | 10 / 31 / 47 | 31 / 40 / 45 |
| sympy/sympy | 75 | 15 / 27 / 36 | 23 / 39 / 41 |
| matplotlib/matplotlib | 23 | 2 / 6 / 7 | 5 / 9 / 9 |
| scikit-learn/scikit-learn | 11 | 1 / 4 / 5 | 6 / 6 / 6 |
| pytest-dev/pytest | 16 | 0 / 1 / 5 | 3 / 6 / 7 |
| sphinx-doc/sphinx | 16 | 0 / 5 / 8 | 1 / 3 / 7 |
| astropy/astropy | 6 | 1 / 1 / 4 | 2 / 4 / 4 |
| psf/requests | 6 | 1 / 2 / 2 | 1 / 2 / 3 |
| pylint-dev/pylint | 6 | 0 / 0 / 0 | 0 / 0 / 1 |
| pydata/xarray | 5 | 0 / 1 / 1 | 1 / 1 / 1 |
| mwaskom/seaborn | 4 | 0 / 0 / 0 | 3 / 3 / 4 |
| pallets/flask | 3 | 2 / 2 / 2 | 2 / 2 / 3 |
| **all** | **285** | **32 / 80 / 117** | **78 / 115 / 131** |

tokens handed to the model per issue: Model D 521, Graphify 1,520

#### Query: title + 400 characters

| repo | issues | Model D top-1 / 3 / 5 | Graphify top-1 / 3 / 5 |
|---|---|---|---|
| django/django | 114 | 21 / 51 / 64 | 32 / 43 / 53 |
| sympy/sympy | 75 | 25 / 40 / 44 | 15 / 24 / 31 |
| matplotlib/matplotlib | 23 | 2 / 9 / 11 | 1 / 4 / 4 |
| scikit-learn/scikit-learn | 11 | 3 / 6 / 8 | 7 / 7 / 7 |
| pytest-dev/pytest | 16 | 0 / 3 / 7 | 3 / 6 / 6 |
| sphinx-doc/sphinx | 16 | 2 / 7 / 7 | 2 / 4 / 6 |
| astropy/astropy | 6 | 4 / 4 / 6 | 2 / 2 / 3 |
| psf/requests | 6 | 3 / 4 / 4 | 1 / 3 / 4 |
| pylint-dev/pylint | 6 | 2 / 2 / 3 | 1 / 1 / 1 |
| pydata/xarray | 5 | 1 / 1 / 1 | 2 / 3 / 3 |
| mwaskom/seaborn | 4 | 0 / 0 / 0 | 0 / 1 / 3 |
| pallets/flask | 3 | 1 / 2 / 2 | 1 / 1 / 1 |
| **all** | **285** | **64 / 129 / 157** | **67 / 99 / 122** |

tokens handed to the model per issue: Model D 617, Graphify 1,652

issues dropped (no fixed file in the snapshot): {'sympy/sympy': 2, 'scikit-learn/scikit-learn': 12, 'pytest-dev/pytest': 1}
