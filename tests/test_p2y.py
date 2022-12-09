# No need to import fixtures - added by pytest "automagically"

def test_p2y_calculation(aiida_local_code_factory, clear_database):
    from aiida.engine import run
    from aiida.plugins import CalculationFactory

    preprocessing_code = aiida_local_code_factory(entry_point='yambo.yambo', executable='p2y')
    code = aiida_local_code_factory(entry_point='yambo.yambo', executable='yambo')
    # ...
    inputs = { 
            'code': code,
            'preprocessing_code': preprocessing_code,
            'parent_folder':parent,
            'precode_parameters' : orm.Dict(dict={}),
            'settings' : orm.Dict(dict={'INITIALISE': True, 'COPY_DBS': False}),
            'parameters': orm.Dict(dict={'arguments': [],'variables': {}}),
            }

    # submit a calculation using this code ...
    result = run(CalculationFactory('yambo.yambo'), **inputs)

    # check outputs of calculation
    assert result['...'] == ...
