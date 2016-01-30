from flonda.requirements import eval_env_marker

def test_environment_markers():


    assert eval_env_marker("platform.machine == 'i386'", "3.5", "linux", "32") == True
    assert eval_env_marker("platform.machine == 'i386'", "3.5", "linux", "64") == False


    assert eval_env_marker("python_version == '3.4' or python_version == '3.5'", "3.5", "linux", "64") == True
    assert eval_env_marker("python_version == '3.4' or python_version == '3.5'", "3.6", "linux", "64") == False


    assert eval_env_marker("'linux' in sys.platform", "3.5", "linux", "64") == True
    assert eval_env_marker("'linux' in sys.platform", "3.5", "win", "64") == False
