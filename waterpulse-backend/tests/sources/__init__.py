"""One module per data source (or source family). Each registers its probes
with the shared registry via the @register decorator in `._base`.
`tests.matrix` imports every module here so the registry is fully populated."""
