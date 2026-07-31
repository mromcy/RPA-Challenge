from botcity.maestro import BotMaestroSDK

from resources.settings import get_settings

settings = get_settings()


def login() -> BotMaestroSDK:
    maestro = BotMaestroSDK()
    maestro.login(
        server=settings.SERVER_BOTCITY,
        login=settings.LOGIN_BOTCITY,
        key=settings.KEY_BOTCITY,
    )
    return maestro


def create_task(maestro: BotMaestroSDK):
    params = {}
    task = maestro.create_task(
        activity_label=settings.PROJECT_NAME, parameters=params, test=True
    )
    return task
