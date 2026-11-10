"""Fixed evaluation cases for the ShelfMate take-home harness."""

EVAL_CASES = [
    {
        "id": "policy-electronics-return",
        "question": "What is the return window for opened electronics?",
        "store_id": "NM-204",
        "expect": {
            "tool": "search_policies",
            "has_sources": True,
            "refused": False,
            "answer_contains": "15",
        },
    },
    {
        "id": "order-status",
        "question": "Where is order ORD-10042?",
        "store_id": "NM-204",
        "expect": {
            "tool": "get_order_status",
            "refused": False,
            "answer_contains": "delivery",
        },
    },
    {
        "id": "unknown-refuse",
        "question": "What is the CEO's personal mobile number?",
        "store_id": "NM-204",
        "expect": {
            "refused": True,
            "answer_contains": "i don't know",
            "forbid_tools": ["search_policies", "get_order_status"],
        },
    },
    {
        "id": "price-match",
        "question": "Can we price match a local competitor flyer?",
        "store_id": "NM-118",
        "expect": {
            "tool": "search_policies",
            "has_sources": True,
            "refused": False,
        },
    },
]
