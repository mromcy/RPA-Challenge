"""
Testes do laço de processamento da fila (Executers/execute_challenge.py).

Rodam sem navegador e sem banco: o driver é o FakeDriver e o banco é um
MagicMock, do qual só interessa **quais chamadas** foram feitas — é assim que se
verifica a máquina de estados por item sem PostgreSQL nenhum.
"""

from unittest.mock import MagicMock

from resources.Executers.execute_challenge import executar_challenge
from resources.Schemas.item_run import Item, ItemInfo, ItemRun, ItemRunStatus
from resources.Schemas.process_run import ProcessRun
from tests.fake_driver import FakeDriver

URL = 'https://exemplo.invalido/'

PROCESS_RUN = ProcessRun(
    run_id=1,
    process_name='teste',
    resource_name='maquina',
    scheduled_by='marco',
    area='teste',
    status='RUNNING',
)


def _item_info(item_id: int, primeiro_nome: str) -> ItemInfo:
    return ItemInfo(
        process_run=PROCESS_RUN,
        item=Item(
            id=item_id,
            item_id=item_id,
            First_Name=primeiro_nome,
            Last_Name='Sobrenome',
            Company_Name='Empresa',
            Role_in_Company='Cargo',
            Address='Endereço',
            Email='email@exemplo.invalido',
            Phone_Number='999',
        ),
        item_run=ItemRun(
            item_id=item_id,
            run_id=1,
            process_name='teste',
            item_key=f'chave_{item_id}',
            area='teste',
            priority=0,
            status=ItemRunStatus.QUEUED.value,
            tags='',
            resource_name='maquina',
            attempt=0,
        ),
    )


class DriverQueFalhaEm(FakeDriver):
    """FakeDriver que estoura ao preencher o nome indicado."""

    def __init__(self, nome_problematico: str):
        super().__init__()
        self._nome_problematico = nome_problematico

    def preencher_campo(self, rotulo: str, valor: str) -> None:
        if valor == self._nome_problematico:
            raise RuntimeError(f'campo recusado: {valor}')
        super().preencher_campo(rotulo, valor)


def _status_gravados(db: MagicMock, status: ItemRunStatus) -> list[int]:
    """item_ids que receberam aquele status, na ordem em que foram gravados."""
    return [
        chamada.args[0]
        for chamada in db.update_item_run_status.call_args_list
        if chamada.args[1] == status
    ]


def test_todos_os_itens_marcados_como_completed_sem_falha():
    """
    As asserções olham o **banco**, não um número devolvido: é lá que a contagem
    é lida na hora de reportar, então é lá que o teste precisa verificar.
    """
    db = MagicMock()
    itens = [_item_info(1, 'Ana'), _item_info(2, 'Bruno')]

    resultado = executar_challenge(FakeDriver(), MagicMock(), itens, URL, db)

    assert _status_gravados(db, ItemRunStatus.COMPLETED) == [1, 2]
    assert _status_gravados(db, ItemRunStatus.FAILED) == []
    assert '100%' in resultado


def test_item_com_erro_nao_interrompe_os_seguintes():
    """
    O comportamento que justifica manter estado por item: numa carga de 5.000
    registros, um dado ruim no meio não pode impedir os seguintes de serem
    tentados. Antes desta mudança o laço abortava no primeiro erro.
    """
    db = MagicMock()
    itens = [_item_info(1, 'Ana'), _item_info(2, 'Bruno'), _item_info(3, 'Carla')]

    executar_challenge(DriverQueFalhaEm('Bruno'), MagicMock(), itens, URL, db)

    assert _status_gravados(db, ItemRunStatus.COMPLETED) == [1, 3]
    assert _status_gravados(db, ItemRunStatus.FAILED) == [2]


def test_item_com_erro_e_marcado_como_failed_com_o_motivo():
    db = MagicMock()
    item_bom = _item_info(1, 'Ana')
    item_ruim = _item_info(2, 'Bruno')

    executar_challenge(
        DriverQueFalhaEm('Bruno'), MagicMock(), [item_bom, item_ruim], URL, db
    )

    falhas = [
        chamada
        for chamada in db.update_item_run_status.call_args_list
        if chamada.args[1] == ItemRunStatus.FAILED
    ]
    assert len(falhas) == 1
    # A asserção seguinte lê item_run.item_id, que o schema declara opcional.
    # Escrever a suposição aqui troca um AttributeError em None por uma falha
    # que diz qual premissa do teste deixou de valer.
    assert item_ruim.item_run is not None
    assert falhas[0].args[0] == item_ruim.item_run.item_id
    assert 'campo recusado' in falhas[0].kwargs['exception_reason']


def test_resultado_so_e_gravado_nos_itens_que_deram_certo():
    """
    Quem falhou não recebe a taxa de sucesso final: o campo `result` do item
    ficaria dizendo que ele foi processado quando não foi.
    """
    db = MagicMock()
    itens = [_item_info(1, 'Ana'), _item_info(2, 'Bruno'), _item_info(3, 'Carla')]

    executar_challenge(DriverQueFalhaEm('Bruno'), MagicMock(), itens, URL, db)

    ids_gravados = db.update_items_result.call_args.args[0]
    assert ids_gravados == [1, 3]
