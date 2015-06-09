import abc

from traits.api import *
from sympy.core.expr import Expr
import sympy
import numpy as np

from symfit.core.argument import Parameter, Variable
from symfit.core.support import seperate_symbols, sympy_to_scipy, sympy_to_py
from leastsqbound import leastsqbound


class ParameterList(HasStrictTraits):
    __params = List(Parameter)
    __popt = Array
    __pcov = Array

    def __init__(self, params, popt, pcov, *args, **kwargs):
        super(ParameterList, self).__init__(*args, **kwargs)
        self.__params = params
        self.__popt = popt
        self.__pcov = pcov

    def __iter__(self):
        return iter(self.__params)

    def __getattr__(self, name):
        """
        A user can access the value of a parameter directly through this object.
        :param name: Name of a param in __params.
        Naming convention:
        let a = Parameter(). Then:
        .a gives the value of the parameter.
        .a_stdev gives the standard deviation.
        """
        parts = name.split('_')
        param_name = parts.pop(0)
        for key, param in enumerate(self.__params):
            if param.name == param_name:
                if len(parts) == 1:  # There was something appended to the name of the param
                    if parts[0] in ['stdev']:
                        return np.sqrt(self.__pcov[key, key])
                elif len(parts) > 1:
                    raise AttributeError('Illegal attribute ' + name)
                else:  # Only a name was specified, so return the param.
                    return self.__popt[key]
        else:  # No match found, so no param with this name exists.
            raise AttributeError('No Parameter by the name {}.'.format(param_name))

    def get_value(self, param):
        """
        :param param: Parameter object.
        :return: returns the numerical value of param
        """
        assert(isinstance(param, Parameter))
        key = self.__params.index(param)  # Number of param
        return self.__popt[key]

    def get_stdev(self, param):
        """
        :param param: Parameter object.
        :return: returns the standard deviation of param
        """
        assert(isinstance(param, Parameter))
        key = self.__params.index(param)  # Number of param
        return np.sqrt(self.__pcov[key, key])


class FitResults(HasStrictTraits):
    params = Instance(ParameterList)
    infodic = Dict
    mesg = Str
    ier = Int
    ydata = Array
    r_squared = Property(Float)  # Read-only property.

    def __init__(self, params, popt, pcov,  *args, **kwargs):
        """
        Class to display the results of a fit in a nice and unambiquis way.
        All things related to the fit are available on this class, e.g.
        - paramameters + stdev
        - R squared (Regression coefficient.
        - more in the future?
        """
        super(FitResults, self).__init__(*args, **kwargs)
        self.params = ParameterList(params, popt, pcov)

    def __str__(self):
        res = '\nParameter Value        Standard Deviation\n'
        for p in self.params:
            res += '{:10}{:e} {:e}\n'.format(p.name, self.params.get_value(p), self.params.get_stdev(p), width=20)

        res += 'Fitting status message: {}\n'.format(self.mesg)
        res += 'Number of iterations:   {}\n'.format(self.infodic['nfev'])
        res += 'Regression Coefficient: {}\n'.format(self.r_squared)
        return res

    def _get_r_squared(self):
        """
        Getter for the r_sqaured property.
        :return: Regression coefficient.
        """
        ss_err=(self.infodic['fvec']**2).sum()
        ss_tot=((self.ydata-self.ydata.mean())**2).sum()
        return 1-(ss_err/ss_tot)

    # def get_value(self, param):
    #     """
    #     :param param: Parameter object.
    #     :return: returns the numerical value of param
    #     """
    #     key = self.params.index(param)  # Number of param
    #     return self.popt[key]
    #
    # def get_stdev(self, param):
    #     """
    #     :param param: Parameter object.
    #     :return: returns the standard deviation of param
    #     """
    #     key = self.params.index(param)  # Number of param
    #     return self.pcov[key][key]


class BaseFit(ABCHasStrictTraits):
    model = Instance(Expr)
    xdata = Array
    ydata = Array
    params = List(Parameter)
    vars = List(Variable)
    scipy_func = Callable
    fit_results = Instance(FitResults)
    jacobian = Property(depends_on='model')

    def __init__(self, model, *args, **kwargs):
        """
        :param model: sympy expression.
        :param x: xdata to fit to.  NxM
        :param y: ydata             Nx1
        """
        super(BaseFit, self).__init__(*args, **kwargs)
        self.model = model
        # Get all parameters and variables from the model.
        self.vars, self.params = seperate_symbols(self.model)
        # Compile a scipy function
        self.scipy_func = sympy_to_scipy(self.model, self.vars, self.params)

    def get_jacobian(self, p, func, x, y):
        """
        Create the jacobian of the model. This can then be used by
        :return:
        """
        funcs = []
        for jac in self.jacobian:
            res = jac(x, p)
            # If only params in f, we must multiply with an array to preserve the shape of x
            try:
                len(res)
            except TypeError: # not itterable
                res *= np.ones(len(x))
            finally:
                # res = np.atleast_2d(res)
                funcs.append(res)
        ans = np.array(funcs).T
        return ans

    def get_bounds(self):
        """
        :return: List of tuples of all bounds on parameters.
        """

        return [(np.nextafter(p.value, 0), p.value) if p.fixed else (p.min, p.max) for p in self.params]

    @cached_property
    def _get_jacobian(self):
        jac = []
        for param in self.params:
            # Differentiate to every param
            f = sympy.diff(self.model, param)
            # Make them into pythonic functions
            jac.append(sympy_to_scipy(f, self.vars, self.params))
        return jac

    @abc.abstractmethod
    def execute(self, *args, **kwargs):
        return

    @abc.abstractmethod
    def get_initial_guesses(self):
        return

    @abc.abstractmethod
    def error(self, p, func, x, y):
        """
        Error function to be minimalised. Depending on the algorithm, this can
        return a scalar or a vector.
        :param p: guess params
        :param func: scipy_func to fit to
        :param x: xdata
        :param y: ydata
        :return: scalar of vector.
        """
        return


class Fit(BaseFit):
    def __init__(self, model, x, y, *args, **kwargs):
        """
        :param model: sympy expression.
        :param x: xdata to fit to.  NxM
        :param y: ydata             Nx1
        """
        super(Fit, self).__init__(model, *args, **kwargs)
        # We assume the to be at least 2d always.
        # This because we use x = [] for the scipy functions.
        # self.xdata = np.expand_dims(x, axis=0) if len(x.shape) == 1 else x
        # self.xdata = np.atleast_2d(x)
        self.xdata = x
        self.ydata = y
        # Check if the number of variables matches the dim of x
        if len(self.vars) not in x.shape and not len(x.shape) == 1:
            raise Exception('number of vars does not match the shape of the input x data.')

    def execute(self, *args, **kwargs):
        """
        Run fitting and initiate a fit report with the result.
        :return: FitResults object
        """
        popt, cov_x, infodic, mesg, ier = leastsqbound(
            self.error,
            self.get_initial_guesses(),
            args=(self.scipy_func, self.xdata, self.ydata),
            bounds=self.get_bounds(),
            Dfun=self.get_jacobian,
            full_output=True,
            *args,
            **kwargs
        )

        s_sq = (infodic['fvec']**2).sum()/(len(self.ydata)-len(popt))
        # For fixed parameters, there is no stdev.
        pcov =  cov_x*s_sq
        self.fit_results = FitResults(
            params=self.params,
            popt=popt,
            pcov=pcov,
            infodic=infodic,
            mesg=mesg,
            ier=ier,
            ydata=self.ydata,  # Needed to calculate R^2
        )
        return self.fit_results

    def error(self, p, func, x, y):
        """
        :param p: param vector
        :param func: pythonic function
        :param x: xdata
        :param y: ydata
        :return: difference between the data and the fit for the given params.
        This function and get_jacobian should have been staticmethods, but that
        way get_jacobian does not work.
        """
        return func(x, p) - y

    def get_initial_guesses(self):
        """
        Constructs a list of initial guesses from the Parameter objects.
        If no initial value is given, 1.0 is used.
        :return: list of initial guesses for self.params.
        """
        return np.array([param.value for param in self.params])


# class MinimizeParameters(BaseFit):
#     def execute(self, *args, **kwargs):
#         """
#         Run fitting and initiate a fit report with the result.
#         :return: FitResults object
#         """
#         from scipy.optimize import minimize
#
#         # s_sq = (infodic['fvec']**2).sum()/(len(self.ydata)-len(popt))
#         # pcov =  cov_x*s_sq
#         # self.fit_results = FitResults(
#         #     params=self.params,
#         #     popt=popt, pcov=pcov, infodic=infodic, mesg=mesg, ier=ier
#         # )
#         # return self.fit_results
#         ans = minimize(
#             self.error,
#             self.get_initial_guesses(),
#             args=(self.scipy_func, self.xdata, self.ydata),
#             # method='L-BFGS-B',
#             # bounds=self.get_bounds(),
#             # jac=self.get_jacobian,
#         )
#         print ans
#         return ans
#
#     def error(self, p, func, x, y):
#         ans = ((self.scipy_func(self.xdata, p) - y)**2).sum()
#         print p
#         return ans

# class Minimize(BaseFit):
#     """ Minimize with respect to the variables.
#     """
#     constraints = List
#     py_func = Callable
#
#     def __init__(self, *args, **kwargs):
#         super(Minimize, self).__init__(*args, **kwargs)
#         self.py_func = sympy_to_py(self.model, self.vars, self.params)
#
#     def execute(self, *args, **kwargs):
#         """
#         Run fitting and initiate a fit report with the result.
#         :return: FitResults object
#         """
#         from scipy.optimize import minimize
#
#         # s_sq = (infodic['fvec']**2).sum()/(len(self.ydata)-len(popt))
#         # pcov =  cov_x*s_sq
#         # self.fit_results = FitResults(
#         #     params=self.params,
#         #     popt=popt, pcov=pcov, infodic=infodic, mesg=mesg, ier=ier
#         # )
#         # return self.fit_results
#         ans = minimize(
#             self.error,
#             np.array([[-1.0], [1.0]]),
#             method='SLSQP',
#             # bounds=self.get_bounds()
#             # constraints = self.get_constraints(),
#             jac=self.get_jacobian,
#             options={'disp': True},
#         )
#         return ans
#
#     def error(self, p0, sign=1.0):
#         ans = sign*self.py_func(*p0)
#         return ans
#
#     def get_jacobian(self, p, sign=1.0):
#         """
#         Create the jacobian of the model. This can then be used by
#         :return:
#         """
#         # funcs = []
#         # for jac in self.jacobian:
#         #     res = sign*jac(p)
#         #     # If only params in f, we must multiply with an array to preserve the shape of x
#         #     funcs.append(res)
#         # ans = np.array(funcs)
#         # return ans
#         return np.array([sign*jac(p) for jac in self.jacobian])
#
#     @cached_property
#     def _get_jacobian(self):
#         return [sympy_to_scipy(sympy.diff(self.model, var), self.vars, self.params) for var in self.vars]
#
#     def get_constraints(self):
#         """
#         self.constraints already exists, but this function gives them in a
#         scipy compatible format.
#         :return: dict of scipy compatile statements.
#         """
#         from sympy import Eq, Gt, Ge, Ne, Lt, Le
#         cons = []
#         # Minimalize only has two types: equality constraint or inequality.
#         types = {
#             Eq: 'eq', Gt: 'ineq', Ge: 'ineq', Ne: 'ineq', Lt: 'ineq', Le: 'ineq'
#         }
#
#         def make_jac(constraint, p):
#             sym_jac = []
#             for var in self.vars:
#                 sym_jac.append(sympy.diff(constraint.lhs, var))
#             return np.array([sympy_to_scipy(jac, self.vars, self.params)(p) for jac in sym_jac])
#
#         for constraint in self.constraints:
#             print 'constraints:', constraint, constraint.lhs
#             cons.append({
#                 'type': types[constraint.__class__],
#                 'fun' : sympy_to_scipy(constraint.lhs, self.vars, self.params), # Assume the lhs is the equation.
#                 # 'jac' : lambda p, c=constraint: np.array([self.sympy_to_scipy(sympy.diff(c.lhs, var))(p) for var in self.vars])
#                 'jac' : lambda p, c=constraint: make_jac(c, p)
#             })
#         return cons
#
#
#     def get_initial_guesses(self):
#         """
#         Constructs a list of initial guesses from the Parameter objects.
#         If no initial value is given, 1.0 is used.
#         :return: list of initial guesses for self.params.
#         """
#         return np.array([-1.0 for var in self.vars])
#
#
# class Maximize(Minimize):
#     def error(self, p0, sign=1.0):
#         return super(Maximize, self).error(p0, sign=-1.0*sign)