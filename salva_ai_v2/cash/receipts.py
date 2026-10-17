def record_receipt(db,session_id,method,delta_cents,source,custodian='BAR'):
    """Record a receipt/refund fact in the same transaction as its owner operation."""
    if not db.conn.in_transaction:
        raise RuntimeError('Recebimento exige transação da operação.')
    db.conn.execute('INSERT INTO receipt_events(session_id,occurred_at,method,delta_cents,custodian,source) VALUES(?,?,?,?,?,?)',
        (session_id,db.clock.now().isoformat(),method,delta_cents,custodian,source))
