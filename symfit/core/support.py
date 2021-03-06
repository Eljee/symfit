"""
This module contains a support functions and conveniance methods used 
throughout symfit. Some are used prodominantly internaly, others are 
designed for users.
"""
import re
import numpy as np
from symfit.core.argument import Parameter, Variable
from sympy.utilities.lambdify import lambdify

def seperate_symbols(func):
    """
    Seperate the symbols in symbolic function func. Return them in alphabetical
    order.
    :param func: scipy symbolic function.
    :return: (vars, params), a tuple of all variables and parameters, each 
    sorted in alphabetical order.
    :raises TypeError: only symfit Variable and Parameter are allowed, not sympy
    Symbols.
    """
    params = []
    vars = []
    for symbol in func.free_symbols:
        if isinstance(symbol, Parameter):
            params.append(symbol)
        elif isinstance(symbol, Variable):
            vars.append(symbol)
        else:
            raise TypeError('model contains an unknown symbol type, {}'.format(type(symbol)))
    params.sort(key=lambda symbol: symbol.name)
    vars.sort(key=lambda symbol: symbol.name)
    return vars, params

def sympy_to_py(func, vars, params):
    """
    Turn a symbolic expression into a Python lambda function,
    which has the names of the variables and parameters as it's argument names.
    :param func: sympy expression
    :param vars: variables in this model
    :param params: parameters in this model
    :return: lambda function to be used for numerical evaluation of the model.
    """
    return lambdify((vars + params), func, modules='numpy', dummify=False)

def sympy_to_scipy(func, vars, params):
    """
    Convert a symbolic expression to one scipy digs.
    :param func: sympy expression
    :param vars: variables
    :param params: parameters
    """
    lambda_func = sympy_to_py(func, vars, params)
    def f(x, p):
        """
        Scipy style function.
        :param x: list of arrays, NxM
        :param p: tuple of parameter values.
        """
        x = np.atleast_2d(x)
        y = [x[i] for i in range(len(x))] if len(x[0]) else []
        try:
            ans = lambda_func(*(y + list(p)))
        except TypeError:
            # Possibly this is a constant function in which case it only has Parameters.
            ans = lambda_func(*list(p))# * np.ones(x_shape)
        return ans

    return f

def variables(names):
    """
    Convenience function for the creation of multiple variables.
    :param names: string of variable names. Should be comma seperated.
    Example: x, y = variables('x, y')
    """
    return [Variable(name=name.strip()) for name in names.split(',')]

def parameters(names):
    """
    Convenience function for the creation of multiple parameters.
    :param names: string of parameter names. Should be comma seperated.
    Example: a, b = parameters('a, b')
    """
    return [Parameter(name=name.strip()) for name in names.split(',')]