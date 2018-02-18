py_charm_debug_template = """
<component name="ProjectRunConfigurationManager">
  <configuration default="false" name="{name} debug" type="PythonConfigurationType" factoryName="Python" folderName="Debug" singleton="true">
    <option name="INTERPRETER_OPTIONS" value="" />
    <option name="PARENT_ENVS" value="true" />
    <envs>
      <env name="PYTHONUNBUFFERED" value="1" />
    </envs>
    <option name="SDK_HOME" value="docker://axonius/{container_name}/python3.6" />
    <option name="WORKING_DIRECTORY" value="$PROJECT_DIR$/{run_type}" />
    <option name="IS_MODULE_SDK" value="false" />
    <option name="ADD_CONTENT_ROOTS" value="true" />
    <option name="ADD_SOURCE_ROOTS" value="true" />
    <module name="cortex" />
    <EXTENSION ID="DockerContainerSettingsRunConfigurationExtension">
      <option name="envVars">
        <list>
          <DockerEnvVarImpl>
            <option name="name" value="DOCKER" />
            <option name="value" value="true" />
          </DockerEnvVarImpl>
        </list>
      </option>
      <option name="extraHosts">
        <list />
      </option>
      <option name="links">
        <list />
      </option>
      <option name="networkDisabled" value="false" />
      <option name="networkMode" value="axonius" />
      <option name="portBindings">
        <list>
{ports}
        </list>
      </option>
      <option name="publishAllPorts" value="false" />
      <option name="version" value="1" />
      <option name="volumeBindings">
        <list>
          <DockerVolumeBindingImpl>
            <option name="containerPath" value="/app/" />
            <option name="editable" value="true" />
            <option name="hostPath" value="$PROJECT_DIR$/{run_type}" />
            <option name="readOnly" value="true" />
          </DockerVolumeBindingImpl>
          <DockerVolumeBindingImpl>
            <option name="containerPath" value="/home/axonius/logs" />
            <option name="editable" value="true" />
            <option name="hostPath" value="$PROJECT_DIR$/logs/{container_name}" />
            <option name="readOnly" value="false" />
          </DockerVolumeBindingImpl>
          <DockerVolumeBindingImpl>
            <option name="containerPath" value="/home/axonius/libs" />
            <option name="editable" value="true" />
            <option name="hostPath" value="$PROJECT_DIR$/plugins/axonius-libs/src/libs" />
            <option name="readOnly" value="true" />
          </DockerVolumeBindingImpl>
        </list>
      </option>
    </EXTENSION>
    <EXTENSION ID="PythonCoverageRunConfigurationExtension" enabled="false" sample_coverage="true" runner="coverage.py" />
    <option name="SCRIPT_NAME" value="$PROJECT_DIR$/{run_type}/debug_main.py" />
    <option name="PARAMETERS" value="{name}" />
    <option name="SHOW_COMMAND_LINE" value="false" />
    <option name="EMULATE_TERMINAL" value="false" />
    <option name="MODULE_MODE" value="false" />
    <method />
  </configuration>
</component>"""[1:]

py_charm_debug_port_template = """
          <DockerPortBindingImpl>
            <option name="containerPort" value="{internal_port}" />
            <option name="hostIp" value="" />
            <option name="hostPort" value="{host_port}" />
            <option name="protocol" value="tcp" />
          </DockerPortBindingImpl>"""[1:]
