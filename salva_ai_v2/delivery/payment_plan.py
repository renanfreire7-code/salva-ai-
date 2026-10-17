from dataclasses import asdict
from ..common.errors import BusinessError
from ..common.service import integer


EXTENSIONS=('payment_timing','payment_channel','change_for_cents','link_reference')


def expected_change(total_cents,change_for_cents):
    return max(0,(change_for_cents or total_cents)-total_cents)


def validate_plan(draft,total_cents):
    if draft.payment_timing=='UNSPECIFIED':
        if draft.payment_channel is not None or draft.change_for_cents is not None or draft.link_reference:
            raise BusinessError('Escolha quando e como o cliente vai pagar.')
        return
    if draft.payment_timing not in ('ADVANCE','ON_DELIVERY'):
        raise BusinessError('Escolha pagamento antecipado ou na entrega.')
    allowed=('PIX','LINK') if draft.payment_timing=='ADVANCE' else ('MONEY','PIX','DEBIT','CREDIT')
    if draft.payment_channel not in allowed:
        raise BusinessError('Forma incompatível com o momento do pagamento.')
    if draft.payment_channel=='LINK':
        if draft.payment_method not in ('DEBIT','CREDIT'):
            raise BusinessError('Link exige débito ou crédito à vista conforme o comprovante.')
    elif draft.payment_channel!=draft.payment_method:
        raise BusinessError('Confira a modalidade combinada.')
    if draft.payment_method!='MONEY' and draft.collection!='BAR':
        raise BusinessError('Recebimento digital é confirmado na conta ou maquininha do bar.')
    if draft.change_for_cents is not None:
        integer(draft.change_for_cents,'Troco para',1)
        if draft.payment_channel!='MONEY' or draft.change_for_cents<=total_cents:
            raise BusinessError('Troco para deve ser maior que o total e usado somente em dinheiro na entrega.')
    if draft.link_reference and draft.payment_channel!='LINK':
        raise BusinessError('Referência de link é usada somente no pagamento por link.')


def draft_payload(draft):
    payload=asdict(draft)
    # Preserve fingerprints for callers using the pre-extension seven fields.
    if draft.payment_timing=='UNSPECIFIED' and draft.payment_channel is None and draft.change_for_cents is None and not draft.link_reference:
        for key in EXTENSIONS:
            payload.pop(key)
    return payload
