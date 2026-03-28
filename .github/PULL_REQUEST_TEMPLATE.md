## Summary

- Describe what changed and why.

## Type Of Change

- [ ] Feature
- [ ] Bug fix
- [ ] Refactor
- [ ] Docs
- [ ] Tests
- [ ] CI/CD

## Testing Checklist

- [ ] `ruff check src/ tests/`
- [ ] `pytest tests/unit/ -v`
- [ ] `pytest tests/unit/ --cov=src --cov-report=term-missing`
- [ ] `pytest tests/e2e/test_navigation.py -v --headed`

## Security And Data Handling

- [ ] No secrets committed
- [ ] Inputs validated where relevant
- [ ] Error handling reviewed

## UI And Accessibility (if applicable)

- [ ] Keyboard navigation checked
- [ ] Labels and roles verified
- [ ] Responsive behavior checked

## Notes For Reviewers

- Add any context, caveats, or rollout notes.
