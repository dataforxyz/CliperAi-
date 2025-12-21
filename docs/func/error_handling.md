# Error Handling Patterns

All main functions return:
- `Optional[T]` - Returns `None` on error
- `Dict` with `"success": bool` and `"error": Optional[str]` fields
- Exceptions are logged but not always raised (graceful degradation)

## Common Error Scenarios
1. **File not found** → Returns `None` or empty list
2. **API failure** → Logs error, returns `None`
3. **Invalid input** → Validates early, returns `None` with log
4. **Partial success** → Returns partial results with warnings in logs
