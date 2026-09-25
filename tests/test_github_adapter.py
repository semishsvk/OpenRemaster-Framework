from openremaster.adapters.github import GitHubProjectSpec, GitHubReadOnlyAdapter

class FakeReader:
    def resolve_revision(self, repository: str, ref: str) -> str:
        assert repository == "owner/project"
        assert ref == "main"
        return "abc123"

def test_github_adapter_observes_without_mutation_api():
    adapter = GitHubReadOnlyAdapter(
        GitHubProjectSpec("project", "owner/project", "main", "stability-corpus"),
        FakeReader(),
    )
    snapshot = adapter.snapshot()
    assert snapshot.revision == "abc123"
    assert snapshot.metadata["mode"] == "read-only"
    forbidden = {"commit", "push", "write", "delete", "checkout", "branch"}
    assert forbidden.isdisjoint(set(dir(adapter)))
