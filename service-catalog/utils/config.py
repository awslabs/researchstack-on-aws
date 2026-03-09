"""Global configuration singleton for project slug and environment name."""

import os


class GlobalConfig:
    """Holds project_slug and env_name used in stack/role naming."""

    env_name = "dev"
    project_slug = "arc"

    @classmethod
    def set_env_name(cls, env_name: str):
        cls.env_name = env_name

    @classmethod
    def get_env_name(cls) -> str:
        return os.getenv("ENV_NAME", cls.env_name)

    @classmethod
    def set_project_slug(cls, slug: str):
        cls.project_slug = slug

    @classmethod
    def get_project_slug(cls) -> str:
        return cls.project_slug
