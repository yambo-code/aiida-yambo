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
                        self.ctx.first_calc_to_do = 'nscf'

                    elif parent.inputs.parameters.get_dict()['CONTROL']['calculation'] == 'nscf':
                        self.ctx.pw_inputs = self.exposed_inputs(PwBaseWorkChain, 'pw')
                        self.ctx.first_calc_to_do = 'yambo'

                    elif parent.process_type=='aiida.calculations:yambo.yambo':
                        self.ctx.first_calc_to_do = 'yambo'

                    else:
                        self.ctx.previous_pw = False
                        self.report('no valid input calculations, so will start from scratch')
        except:

            self.report('no previous pw calculation found, \
                                we will start from scratch')
            self.ctx.previous_pw = False



        self.report(" workflow initilization step completed.")

    def can_continue(self):
        """This function checks the status of the last calculation and determines what happens next, including a successful exit"""

        if self.ctx.last_step_kind == 'yambo' and self.ctx.yambo_res:

            try:
                self.ctx.yambo_pks.append(
                    self.ctx.yambo_res.outputs.gw.get_dict()["yambo_pk"])
            except AttributeError:
                raise InputValidationError("Yambo input must be a workchain!")
            if self.ctx.yambo_res.outputs.gw.get_dict()["success"] == True:
                self.ctx.done = True
                self.report("Last Yambo calculation was successful, so I will stop here.")

        if self.ctx.last_step_kind == 'yambo_p2y' and self.ctx.yambo_res:
            self.ctx.yambo_pks.append(
                self.ctx.yambo_res.outputs.gw.get_dict()["yambo_pk"])

        if self.ctx.last_step_kind == 'pw' and self.ctx.pw_wf_res != None:
            self.ctx.pw_pks.append(
                self.ctx.pw_wf_res.outputs.pw.get_dict()["nscf_pk"])

        if self.ctx.done == True:
            self.report("Workflow has finished. will report outputs")
            return False
        self.ctx.can_cont += 1
        if self.ctx.can_cont > 10:
            return False
        return True

    def perform_next(self):
        """This function  will submit the next step, depending on the information provided in the context

        The next step will be a yambo calculation if the provided inputs are a previous yambo/p2y run
        Will be a PW scf/nscf if the inputs do not provide the NSCF or previous yambo parent calculations"""

        if self.ctx.last_step_kind == 'yambo' or self.ctx.last_step_kind == 'yambo_p2y':
            if load_node(self.ctx.yambo_res.outputs.gw.get_dict()["yambo_pk"]).is_finished:

                if self.inputs.to_set_qpkrange   and 'QPkrange'\
                        not in list(self.ctx.parameters_yambo.get_dict().keys()):
                    self.ctx.parameters_yambo = default_qpkrange( self.ctx.pw_wf_res.outputs.pw.get_dict()["nscf_pk"],\
                             self.ctx.parameters_yambo)

                if self.inputs.to_set_bands   and ('BndsRnXp' not in list(self.ctx.parameters_yambo.get_dict().keys())\
                        or 'GbndRnge' not in list(self.ctx.parameters_yambo.get_dict().keys())):
                    self.ctx.parameters_yambo = default_bands( self.ctx.pw_wf_res.outputs.pw.get_dict()["nscf_pk"],\
                            self.ctx.parameters_yambo)

                start_from_initialize = load_node(self.ctx.yambo_res.outputs.gw.get_dict()\
                                        ["yambo_pk"]).inputs.settings.get_dict().pop('INITIALISE', None)

                if start_from_initialize:  # YamboRestartWf will initialize before starting QP calc  for us,  INIT != P2Y
                    self.report(
                        "YamboRestartWf will start from initialise mode (yambo init) "
                    )
                    yambo_result = self.run_yambo()
                    return ToContext(yambo_res=yambo_result)

                else:  # Possibly a restart,  after some type of failure, why was not handled by YamboRestartWf? maybe restarting whole workchain
                    self.report(" Restarting {}, this is some form of restart for the workchain".format(\
                            self.ctx.last_step_kind)  )
                    yambo_result = self.run_yambo()
                    return ToContext(yambo_res=yambo_result)

            if len(self.ctx.yambo_pks) > 0:
                if not load_node(self.ctx.yambo_pks[-1]).is_finished_ok:  # Needs a resubmit depending on the error.
                    self.report("Last {} calculation (pk: {}) failed, will attempt a restart".format(\
                            self.ctx.last_step_kind, self.ctx.yambo_pks[-1] ))

        if self.ctx.last_step_kind == 'pw' and self.ctx.pw_wf_res:
            if self.ctx.pw_wf_res.outputs.pw.get_dict()["success"] == True:
                self.report(
                    "PwRestartWf was successful,  running P2Y next with: YamboRestartWf "
                )
                p2y_result = self.run_p2y()
                return ToContext(yambo_res=p2y_result)
            if self.ctx.pw_wf_res.outputs.pw.get_dict()["success"]== False:
                self.report("PwRestartWf subworkflow  NOT  successful")
                return

        if self.ctx.last_step_kind == None or self.ctx.last_step_kind == 'pw' and not self.ctx.pw_wf_res:
            # this is likely  the very beginning, we can start with the scf/nscf here
            extra = {}
            self.report("Launching PwRestartWf ")
            if 'parameters_pw_nscf' in list(self.inputs.keys()):
                extra['parameters_nscf'] = self.inputs.parameters_pw_nscf
            if 'calculation_set_pw_nscf' in list(self.inputs.keys()):
                extra[
                    'calculation_set_pw_nscf'] = self.inputs.calculation_set_pw_nscf
            if 'settings_pw_nscf' in list(self.inputs.keys()):
                extra['settings_pw_nscf'] = self.inputs.settings_pw_nscf
            if 'kpoint_pw_nscf' in list(self.inputs.keys()):
                extra['kpoint_pw_nscf'] = self.inputs.kpoint_pw_nscf
            if 'restart_options_pw' in list(self.inputs.keys()):
                extra['restart_options'] = self.inputs.restart_options_pw
            if 'parent_folder' in list(self.inputs.keys()):
                extra['parent_folder'] = self.inputs.parent_folder
            pw_wf_result = self.run_pw(extra)
            return ToContext(pw_wf_res=pw_wf_result)

    def run_yambo(self):
        """ submit a yambo calculation """
        extra = {}
        if 'restart_options_pw' in list(self.inputs.keys()):
            extra['restart_options'] = self.inputs.restart_options_pw
        parentcalc = load_node(
            self.ctx.yambo_res.outputs.gw.get_dict()["yambo_pk"])
        parent_folder = parentcalc.outputs.remote_folder
        yambo_result = self.submit(
            YamboRestartWf,
            precode=self.inputs.codename_p2y,
            yambocode=self.inputs.codename_yambo,
            parameters=self.ctx.parameters_yambo,
            calculation_set=self.inputs.calculation_set_yambo,
            parent_folder=parent_folder,
            settings=self.inputs.settings_yambo,
            **extra)
        self.ctx.last_step_kind = 'yambo'
        self.report(
            "submitted YamboRestartWf subworkflow, in Initialize mode  ")
        return yambo_result

    def run_p2y(self): #si fa in un solo step p2y e yambo...
        """ submit a  P2Y  calculation """
        extra = {}
        if 'restart_options_gw' in list(self.inputs.keys()):
            extra['restart_options'] = self.inputs.restart_options_pw
        parentcalc = load_node(self.ctx.pw_wf_res.outputs.pw.get_dict()["nscf_pk"])
        parent_folder = parentcalc.outputs.remote_folder
        p2y_result = self.submit(
            YamboRestartWf,
            precode=self.inputs.codename_p2y,
            yambocode=self.inputs.codename_yambo,
            parameters=self.inputs.parameters_p2y,
            calculation_set=self.inputs.calculation_set_p2y,
            parent_folder=parent_folder,
            settings=self.inputs.settings_p2y,
            **extra)
        self.ctx.last_step_kind = 'yambo_p2y'
        return p2y_result

    def run_pw(self, extra):
        """ submit a PW calculation """
        pw_wf_result = self.submit(
            PwRestartWf,
            codename=self.inputs.codename_pw,
            pseudo_family=self.inputs.pseudo_family,
            calculation_set=self.inputs.calculation_set_pw,
            settings=self.inputs.settings_pw,
            kpoints=self.inputs.kpoint_pw,
            gamma=self.inputs.gamma_pw,
            structure=self.inputs.structure,
            parameters=self.inputs.parameters_pw,
            **extra)
        self.ctx.last_step_kind = 'pw'
        return pw_wf_result

    def run_restart(self):
        """ submit a followup yambo calculation """
        extra = {}
        if 'restart_options_gw' in list(self.inputs.keys()):
            extra['restart_options'] = self.inputs.restart_options_pw
            parentcalc = load_node(   #maybe...
                self.ctx.yambo_res.outputs.gw.get_dict()["yambo_pk"])
            parent_folder = parentcalc.outputs.remote_folder
        yambo_result = self.submit(
            YamboRestartWf,
            precode=self.inputs.codename_p2y,
            yambocode=self.inputs.codename_yambo,
            parameters=self.ctx.parameters_yambo,
            calculation_set=self.inputs.calculation_set_yambo,
            parent_folder=parent_folder,
            settings=self.inputs.settings_yambo,
            **extra)
        self.ctx.last_step_kind = 'yambo'
        self.report(
            "submitted YamboRestartWf subworkflow, in Initialize mode  ")
        return yambo_result

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
