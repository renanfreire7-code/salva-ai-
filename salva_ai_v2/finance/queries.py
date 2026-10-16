import calendar
from datetime import date
from ..common.errors import BusinessError


def month_range(month):
    try:
        if len(month)!=7:
            raise ValueError()
        start=date.fromisoformat(month+"-01")
        return start,date(start.year,start.month,calendar.monthrange(start.year,start.month)[1])
    except (ValueError,TypeError):
        raise BusinessError("Mês inválido. Utilize AAAA-MM.") from None

