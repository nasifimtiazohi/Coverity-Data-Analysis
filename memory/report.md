# Introduction:
Software development is an error-prone activity. Code written and reviewed by skilled developers may end up with various types of bugs some of which can be security-critical, i.e. vulnerability. Developers use various security testing tools (e.g. static analysis, fuzzing) in order
to identify the potential vulnerabilities. However, given the non-perfect nature of these tools and the cost of fixing the alerts they generate, developers response to such alerts may vary. Further, even after extensive security testing, undetected vulnerabilities may still remain in code that get discovered years after it was introduced.

Memory-related bugs, such as buffer overflows and uninitialized reads, are an important class of security vulnerabilities typically more prevalent in non memory-safe languages such as C, C++. Security analysis techniques such as static analysis can detect a wide range of potential memory issues in the code. Tools performing such analysis present their results as alerts to the developers. However, it is yet to be studied how frequently does memory-related alerts are identified by security tools and how developers respond to them. Vulnerabilities that leak through all cautionary approaches taken by the developers, may get discovered years later. If reported to the National Vulnerability Database (NVD), these vulnerabilities are tracked in a central database with a unique identifier called CVE. However, it is yet to be studied if these vulnerabilities (CVEs) appeared in the code because security testing procedures failed to identify them or the testing had indeed identified the flaw but due to a lack of corrective developer action.

In this paper, we study 10 C/C++ projects that have been using a static analysis security testing tool. We analyze the historical scan reports by the tool for these projects and study how frequently memory-related alerts occurred and developers acted on those alerts. For one of this project, Linux, we also look at the CVEs that were published and investigate if the involved flaw in those vulnerabilities were identified by the security tool when they were first introduced. We state our research questions as:

- **RQ1:** How frequently memory alerts are identified by a static analysis security testing tool? How do developers respond to these alerts?
- **RQ2:** How many CVEs was identified by a static analysis security testing tool when the CVEs were first introduced in the code?

# Dataset:
Coverity dataset: We have a dataset from prior work that we extended.
#CVE dataset:
CWE classification for memory vs. non-memory:

# Findings:

# Discussion:

# Threats to validity:

# Conclusion
