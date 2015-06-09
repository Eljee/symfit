Documentation
=============
http://symfit.readthedocs.org

Project Goals
=============
## Why this Project?
Existing fitting modules are not very pythonic in their API and can be difficult for humans to use. This project aims to marry the power of scipy.optimize with SymPy to create an highly readable and easy to use fitting package which works for projects of any scale.

The example below shows how easy it is to define a model that we could fit to.
```python
from symfit.api import Parameter, Variable
import sympy

x0 = Parameter()
sig = Parameter()
x = Variable()
gaussian = sympy.exp(-(x - x0)**2/(2*sig**2))/(2*sympy.pi*sig)
```

Lets fit this model to some generated data.

```python
from symfit.api import Fit

xdata = # Some numpy array of x values
ydata = # Some numpy array of y values, gaussian distribution
fit = Fit(gaussian, xdata, ydata)
fit_result = fit.execute()
```
Printing ```fit_result``` will give a full report on the values for every parameter, including the uncertainty, and quality of the fit.

Adding guesses for ```Parameter```'s is simple: ```Parameter(1.0)``` or ```Parameter{value=1.0)```. Let's add another step: suppose we are able to estimate bounds for the parameter as well, for example by looking at a plot. We could then do this: ```Parameter(2.0, min=1.5, max=2.5)```. Complete example:

```python
from symfit.api import Fit, Parameter, Variable
import sympy

x0 = Parameter(2.0, min=1.5, max=2.5)
sig = Parameter()
x = Variable()
gaussian = sympy.exp(-(x - x0)**2/(2*sig**2))/(2*sympy.pi*sig)

xdata = # Some numpy array of x values
ydata = # Some numpy array of y values, gaussian distribution
fit = Fit(gaussian, xdata, ydata)
fit_result = fit.execute()
```

The ```Parameter``` options do not stop there. If a parameter is completely fixed during the fitting, we could use ```Parameter(2.0, fixed=True)``` which is mutually exclusive with the ```min, max``` keywords.

Using this paradigm it is easy to buil multivariable models and fit to them:

```python
from symfit.api import Parameter, Variable
from sympy import exp, pi

x0 = Parameter()
y0 = Parameter()
sig_x = Parameter()
sig_y = Parameter()
x = Variable()
y = Variable()
gaussian_2d = exp(-((x - x0)**2/(2*sig_x**2) + (y - y0)**2/(2*sig_y**2)))/(2*pi*sig_x*sig_y)
```

Because of the symbolic nature of this program, the Jacobian of the model can always be determined. Although scipy can approximate the Jacobian numerically, it is not always able to approximate the covariance matrix from this. But this is needed if we want to calculate the errors in our parameters.

This project will always be able to do as long, assuming your model is differentiable. This means we can do proper error propagation.

##Models are Callable
```python 
a = Parameter()
x = Variable()
f = a * x**2
print f(x=3, a=2)
```
They must always be called through keyword arguments to prevent any ambiguity in which parameter or variable you mean.

####Optional Arguments

Knowing that symfit is (currently just) a wrapper to SciPy, you could decide to look in their documentation to specify extra options for the fitting. These extra arguments can be provided to ```execute```, as it will pass on any ```*args, **kwargs``` to leastsq or minimize depending on the context.

FitResults
==========
The FitResults object which is returned by Fit.execute contains all information about the fit. Let's look at this by looking at an example:
```python
from symfit.api import Fit, Parameter, Variable
import sympy

x0 = Parameter(2.0, min=1.5, max=2.5)
sig = Parameter()
x = Variable()
gaussian = sympy.exp(-(x - x0)**2/(2*sig**2))/(2*sympy.pi*sig)

xdata = # Some numpy array of x values
ydata = # Some numpy array of y values, gaussian distribution
fit = Fit(gaussian, xdata, ydata)
fit_result = fit.execute()

print fit_result.params.x0  # Print the value of x0
print fit_result.params.x0_stdev  # stdev in x0 as obtained from the fit.

try:
    print fit_result.params.x
except AttributeError:  # This will fire
    print 'No such Parameter'
    
print fit_result.r_squared  # Regression coefficient
```
The value/stdev of a parameter can also be obtained in the following way:
```python
fit_result.params.get_value(x0)
fit_result.params.get_stdev(x0)
```
How Does it Work?
=================

####```AbstractFunction```'s
Comming soon

####```Argument```'s
Only two kinds input ```Argument``` are defined for a model: ```Variable``` and ```Parameter```.

API Reference
=============
Parameter
- name (optional)
- value (optional)
    Initial guess for the parameter. 
- min (optional)
- max (optional)

Variable
- name (optional)

### Immidiate Goals
- High code readability and a very pythonic feel.
- Efficient Fitting
- Fitting algorithms for any scale using scipy.optimize. From typical least squares fitting to Multivariant fitting with bounds and constraints using the overkill scipy.optimize.minimize.

### Long Term Goals
- Monte-Carlo
- Error Propagation using the uncertainties package

type: any python-type, such as float or int. default = float. 

~~Advanced Usage~~
==================
Temporaraly disabled because of conceptual misgivings. This feature should be re-enabled in the future however, as it is awesome.

#### Constrained minimization of multivariate scalar functions

Example taken from http://docs.scipy.org/doc/scipy/reference/tutorial/optimize.html

Suppose we want to maximize the following function:

![function](http://docs.scipy.org/doc/scipy/reference/_images/math/775ad8006edfe87928e39f1798d8f53849f7216f.png)

Subject to the following constraits:

![constraints](http://docs.scipy.org/doc/scipy/reference/_images/math/984a489a67fd94bcec325c0d60777d61c12c94f4.png)

In SciPy code the following lines are needed:
```python
def func(x, sign=1.0):
    """ Objective function """
    return sign*(2*x[0]*x[1] + 2*x[0] - x[0]**2 - 2*x[1]**2)
    
def func_deriv(x, sign=1.0):
    """ Derivative of objective function """
    dfdx0 = sign*(-2*x[0] + 2*x[1] + 2)
    dfdx1 = sign*(2*x[0] - 4*x[1])
    return np.array([ dfdx0, dfdx1 ])
    
cons = ({'type': 'eq',
         'fun' : lambda x: np.array([x[0]**3 - x[1]]),
         'jac' : lambda x: np.array([3.0*(x[0]**2.0), -1.0])},
        {'type': 'ineq',
         'fun' : lambda x: np.array([x[1] - 1]),
         'jac' : lambda x: np.array([0.0, 1.0])})
         
res = minimize(func, [-1.0,1.0], args=(-1.0,), jac=func_deriv,
               constraints=cons, method='SLSQP', options={'disp': True})
```
Takes a couple of readthroughs to make sense, doesn't it? Let's do the same problem in symfit:

```python
x = Variable()
y = Variable()
model = 2*x*y + 2*x - x**2 -2*y**2
constraints = [
	x**3 - y == 0,
    y - 1 >= 0,
]

fit = Minimize(model, constraints=constraints)
fit.execute()
```
Done! symfit will determine all derivatives automatically, no need for you to think about it. In order to be consistent with the name in SciPy, ```Minimize``` minimizes with respect to the variables, without taking into acount any data points. To minimize the parameters while constraining the variables, use ```MinimizeParameters``` instead.

```python
fit = MinimizeParameters(model, xdata, ydata, constraints=constraints)
```

Using ```MinimizeParameters``` without ```constraints``` in principle yields the same result as using ```Fit```, which does a least-squares fit. A case could therefore be made for always using ```MinimizeParameters```. However, I cannot comment on whether this is proper usage of the minimalize function.

Note: constraints must be of the type 'expression == scalar.' If this is not the case, please use an Eq object. (from symfit import Eq) For every relation, an object is available:
Eq, Ne, Gt, Lt, Ge, Le.


