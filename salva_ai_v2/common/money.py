from decimal import Decimal, InvalidOperation
from .errors import BusinessError


def round_half_up(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        raise ValueError("Denominador deve ser positivo")
    sign = -1 if numerator < 0 else 1
    whole, rem = divmod(abs(numerator), denominator)
    return sign * (whole + (rem * 2 >= denominator))


def allocate(total_cents: int, weights: dict[int, int]) -> dict[int, int]:
    if total_cents < 0 or any(w < 0 for w in weights.values()):
        raise ValueError("Valores negativos no rateio")
    total = sum(weights.values())
    if not total:
        if total_cents:
            raise BusinessError("Não há base para ratear este valor.")
        return {key: 0 for key in weights}
    result = {key: total_cents * weight // total for key, weight in weights.items()}
    order = sorted(weights, key=lambda key: (-(total_cents * weights[key] % total), key))
    for key in order[:total_cents - sum(result.values())]:
        result[key] += 1
    return result


def parse_money(value: str) -> int:
    try:
        text = str(value).strip().replace("R$", "").strip()
        if "," in text:
            text = text.replace(".", "").replace(",", ".")
        amount = Decimal(text)
        if not amount.is_finite() or amount < 0 or amount != amount.quantize(Decimal(".01")):
            raise ValueError()
        return int(amount * 100)
    except (InvalidOperation, ValueError, TypeError):
        raise BusinessError("Informe um valor positivo com até duas casas decimais.") from None


def money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    whole, fraction = divmod(abs(cents), 100)
    return f"R$ {sign}{whole:,},{fraction:02d}".replace(",", ".", f"{whole:,}".count(","))
