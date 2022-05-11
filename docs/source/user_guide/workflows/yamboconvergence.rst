.. _tut-ref-to-yambo-conv1d:

YamboConvergence: automated GW ans BSE convergences
---------------------------------------------------

The ``YamboConvergence`` workchain provides the functionalities to run multiple G0W0/BSE calculations on the same system, over a wide range of value of parameters. 
This represents the typical method to obtain an accurate evaluation of the quasiparticle correction: indeed, a lot of effort has to be done in order to find
the convergence with respect to parameters like empty states used to evaluate the Self Energy used to solve the quasiparticle equation.
If you implement a logic for convergence evaluation to guide the iter of these multiple parameter-dependent calculations, you can obtain an automatic flow
that allows you to obtain good G0W0/BSE results. This is what YamboConvergence does. The purpose of this new proposed algorithm is to obtain an accurate converged 
result doing the least possible number of calculations. This is possible if a reliable description of the convergence space is achieved, resulting also in a 
precise guess for the converged point, i.e. the converged parameters. The description of the space is performed by fitting some calculations that the workchain runs. 
Following heuristics, a simple functional form of the space is assumed:

\begin{equation}
    \label{multi_over_x}
    f(\textbf{x}) = \prod_i^N \left( \frac{A_i}{x_i^{\alpha_i}} + b_i \right)
\end{equation}

The algorithm is specifically designed to solve the coupled convergence between 
summation over empty states (``BndsRnXp`` or ``BndsRnXs`` and ``GbndRnge`` for example) and PW expansion (``NGsBlkXp`` or ``NGsBlkXs``), but it can be used also to 
accelerate convergence tests with respect to the k-point mesh or ``FFTGvecs``, as we shall see later. 
Moreover, the quantities that we can converge are the ones that can be parsed by the 
``YamboWorkflow`` workchain: quasiparticle levels/gaps, and excitonic energies.

Let's see the case of automatic search of convergence over an arbitrary number of parameters:

Example usage:

.. include:: ../../../../examples/test_wf/yambo_convergence.py
   :literal:

As you can see, we have to provide workflow_settings, which encode some workflow logic:

::

    builder.workflow_settings = Dict(dict={
        'type': 'cheap', #or heavy; cheap uses low parameters for the ones that we are not converging
        'what': ['gap_'],
        'bands_nscf_update': 'full-step'},)

The workflow submitted here looks for convergence on different parameters. The iter is specified
with the input list ``parameters_space``. This is a list of dictionaries, each one representing a given phase of the investigation. 
If `type` is cheap, the converged parameters are re-set to starting one when convergence is performed on the other parameters. This in order to have faster calculations.
Instead, if `type` is heavy, the parameters already converged are taken as the converged value. In this way, at the end of the convergence you will have already done the calculation
and you can start from there with post processing. 
The quantity that tries to converge is the gap('what') between given bands evaluated at fixed k-points. It is possible to choose also and indirect gap(notice that,
changing the k-point mesh, the k-points will change index). The workflow will take care of it and doesn't stop until all the quantities are
converged(or the maximum restarts are reached).

The complete workflow will return the results of the convergence iterations, as well as a final converged calculation, from which we can parse the
converged parameters, and a complete story of all the calculations of the workflow with all the information provided.

To show how the convergence algorithm works, here we plot the convergences performed on 2D-hBN imposing a convergence threshold of 1% on the final gap. The convergence is 
performed with respect to ``NGsBlkXp`` (G_cut in the plot) and ``BndsRnXp`` == ``GbndRnge`` (Nb in the plot). 

.. image:: ./images/2D_conv_hBN.png

We can observe that first simulations (black squares) are performed on a starting grid, the blue one. The algorithm decides then to perform another set of calculations on 
a shifted grid, as the fit perofmed to predict the space was not enough accurate. Next, a converged point is predicted, corresponding to the blue square, and it is explicitely computed. 
Using also the informations on that point, the algorithm understands that a new converged point can be the red one. This is then computed and verified to be the real converged one. In this 
way, convergence is efficiently achieved. 
 
