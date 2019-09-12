from __future__ import absolute_import
import sys
import itertools

class YamboWorkflow(WorkChain):

    """This workflow will perform yambo calculation on the top of scf+nscf or from scratch,
    invoking qe workchains.
    """

    @classmethod
    def define(cls, spec):
        """Workfunction definition

        """
        super(YamboWorkflow, cls).define(spec)

        spec.expose_inputs(PwBaseWorkChain, namespace='pw', \
                            namespace_options={'required': False}, exclude = 'parent_folder')

        spec.expose_inputs(YamboRestartWf, namespace='res_wf', exclude = 'parent_folder')

        spec.input("parent_folder", valid_type=RemoteData, required=False, default = None)
        #spec.input("nscf_params", valid_type=RemoteData, required=False, default = None)

##################################### OUTLINE ####################################

        spec.outline(cls.start_workflow,
                     while_(cls.can_continue)(
                     cls.perform_next),
                     cls.report_wf,
                     )

##################################################################################

        spec.output('yambo_calc_folder', valid_type = RemoteData,
            help='The yambo calculation remote folder.')

    def start_workflow(self):
        """Initialize the workflow, set the parent calculation

        This function sets the parent, and its type, including support for starting from a previos workchain,
        there is no submission done here, only setting up the neccessary inputs the workchain needs in the next
        steps to decide what are the subsequent steps"""

        self.ctx.yambo_inputs = self.exposed_inputs(YamboRestartWf, 'res_wf')

        try:

            with self.inputs.parent_folder.get_incoming().get_node_by_label('remote_folder') as parent:

                if parent.process_type=='aiida.calculations:quantumespresso.pw':

                    self.ctx.previous_pw = True

                    if parent.inputs.parameters.get_dict()['CONTROL']['calculation'] == 'scf':
                        self.ctx.pw_inputs = self.exposed_inputs(PwBaseWorkChain, 'pw')
                        self.ctx.calc_to_do = 'nscf'

                    elif parent.inputs.parameters.get_dict()['CONTROL']['calculation'] == 'nscf':
                        self.ctx.pw_inputs = self.exposed_inputs(PwBaseWorkChain, 'pw')
                        self.ctx.calc_to_do = 'yambo'

                    elif parent.process_type=='aiida.calculations:yambo.yambo':
                        self.ctx.calc_to_do = 'yambo'

                    else:
                        self.ctx.previous_pw = False
                        self.ctx.calc_to_do = 'scf'
                        self.report('no valid input calculations, so will start from scratch')
        except:

            self.report('no previous pw calculation found, \
                                we will start from scratch')
            self.ctx.calc_to_do = 'scf'
            self.ctx.previous_pw = False

        self.report(" workflow initilization step completed.")

    def can_continue(self):

        """This function checks the status of the last calculation and determines what happens next, including a successful exit"""

        if self.ctx.calc_to_do != 'the workflow is finished':
            self.report('the workflow continues with a {} calculation'.format(self.ctx.calc_to_do))
            return True
        else:
            self.report('the workflow is finished')
            return False


    def perform_next(self):
        """This function  will submit the next step, depending on the information provided in the context

        The next step will be a yambo calculation if the provided inputs are a previous yambo/p2y run
        Will be a PW scf/nscf if the inputs do not provide the NSCF or previous yambo parent calculations"""

        if self.ctx.calc_to_do == 'scf':
            ddd

        elif self.ctx.calc_to_do == 'nscf':
            ddd

        elif self.ctx.calc_to_do == 'yambo':
            cscovk

    def report_wf(self):
        """
        """
        self.report('Final step.')
        from aiida.plugins import DataFactory
        #try:
        #    pw = self.ctx.pw_wf_res.outputs.pw.get_dict()
        #except Exception:
        #    pw = {}
        #gw = self.ctx.yambo_res.outputs.gw.get_dict()
        #gw.update(pw)
        #self.out("yambo_remote_folder",self.ctx.yambo_res.outputs.yambo_remote_folder)
        #self.out("scf_remote_folder", self.ctx.pw_wf_res.outputs.scf_remote_folder)
        #self.out("nscf_remote_folder",self.ctx.pw_wf_res.outputs.nscf_remote_folder)
        if self.ctx.bands_groupname is not None:
            g_bands, _ = Group.get_or_create(name=self.ctx.bands_groupname)
            g_bands.add_nodes(self.ctx.yambo_res)
            self.report("Yambo calc (pk: {}) added to the group {}".format(
                self.ctx.yambo_res.pk, self.ctx.bands_groupname))
        else:
            self.report("Yambo calc done (pk: {} ) ".format(self.ctx.yambo_res.pk)) #pero' e' la workchain!!
        self.out("gw", self.ctx.pw_wf_res.outputs.pw)
        self.out("pw", self.ctx.yambo_res.outputs.gw)
        self.report("workflow completed")


if __name__ == "__main__":
    pass
