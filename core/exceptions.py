"""全局异常类型。"""


class DramaAgentError(Exception):
    """项目基础异常。"""


class WorkflowExecutionError(DramaAgentError):
    """工作流执行失败。"""


class ArtifactNotFoundError(DramaAgentError):
    """产物不存在。"""


class ConfigurationError(DramaAgentError):
    """配置错误。"""
