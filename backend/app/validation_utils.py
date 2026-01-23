from typing import List, Dict, Any, Tuple
from pydantic import ValidationError
from . import schemas

MAX_ERROS_POR_TABELA = 50

def _build_issue(tabela: str, index: int, err: Dict[str, Any]) -> schemas.ValidationIssue:
    loc = err.get('loc') or []
    campo = loc[0] if isinstance(loc, (list, tuple)) and loc else 'desconhecido'
    detalhe = err.get('msg') or 'erro de validação'
    return schemas.ValidationIssue(tabela=tabela, index=index, campo=str(campo), detalhe=str(detalhe))

def _validate_lote(records: List[Dict[str, Any]], schema_cls, tabela: str) -> Tuple[List[Dict[str, Any]], schemas.ValidationReport]:
    validos: List[Dict[str, Any]] = []
    erros: List[schemas.ValidationIssue] = []
    for i, r in enumerate(records or []):
        try:
            m = schema_cls.model_validate(r)
            validos.append(m.model_dump())
        except ValidationError as ve:
            for err in ve.errors():
                if len(erros) < MAX_ERROS_POR_TABELA:
                    erros.append(_build_issue(tabela, i, err))
        except Exception as e:
            if len(erros) < MAX_ERROS_POR_TABELA:
                erros.append(schemas.ValidationIssue(tabela=tabela, index=i, campo='__record__', detalhe=str(e)))
    report = schemas.ValidationReport(
        tabela=tabela,
        total=len(records or []),
        validos=len(validos),
        invalidos=(len(records or []) - len(validos)),
        erros=erros,
    )
    return validos, report


def validar_financeiro(records: List[Dict[str, Any]]):
    return _validate_lote(records, schemas.RegistroFinanceiroBase, 'financeiro')


def validar_produtos(records: List[Dict[str, Any]]):
    return _validate_lote(records, schemas.RegistroProdutoBase, 'produtos')


def validar_operacional(records: List[Dict[str, Any]]):
    return _validate_lote(records, schemas.RegistroOperacionalBase, 'operacional')