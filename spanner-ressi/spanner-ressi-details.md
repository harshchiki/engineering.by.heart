# SSTables to Ressi: Re-architecting Storage for HTAP

**Handle:** @engineering.by.heart  
**Format:** 15 portrait carousel images, 2160 x 2700 pixels, 4:5 aspect ratio.  
**Visual direction:** Dark navy, mint, blue, purple and orange; original storage diagrams; consistent slide numbering and handle.  
**Research date:** October 14, 2026.

This companion contains the slide narrative, the technical details reviewed, primary-source links, and corrections to the original blueprint. It summarizes the sources in original language rather than reproducing their text.

## Files and order

| Slide | Image | Topic |
|---|---|---|
| 1 | `01-cover.png` | SSTables to Ressi |
| 2 | `02-core-problem.png` | Relational access over a key-value format |
| 3 | `03-enter-ressi.png` | SQL-aware storage |
| 4 | `04-sstable-layout.png` | Illustrative SSTable layout |
| 5 | `05-pax-layout.png` | Ressi's PAX blocks |
| 6 | `06-query-paths.png` | Point reads versus column scans |
| 7 | `07-encoding-compression.png` | Typed vectors and encoding |
| 8 | `08-htap-breakthrough.png` | Mixed transactional and analytical access |
| 9 | `09-competitive-landscape.png` | Storage-system trade-offs |
| 10 | `10-hidden-complexities.png` | Versions, compaction and migration |
| 11 | `11-when-not-to-use.png` | When not to design a hybrid format |
| 12 | `12-long-term-benefits.png` | Efficiency and preserved guarantees |
| 13 | `13-dedicated-columnar-engine.png` | Pure columnar runs alongside PAX |
| 14 | `14-implementation-takeaways.png` | Measurement-led design |
| 15 | `15-conclusion-cta.png` | Summary and engagement |

`carousel-overview.jpg` is a contact sheet for reviewing all 15 images. Use the individual PNG files for publishing.

## Primary sources reviewed

### S1. Spanner: Becoming a SQL System

- Authors: David F. Bacon and colleagues at Google.
- Publication: SIGMOD 2017.
- DOI: `10.1145/3035918.3056103`.
- [Google Research publication page](https://research.google/pubs/spanner-becoming-a-sql-system/).
- [Full paper PDF](https://storage.googleapis.com/gweb-research2023-media/pubtools/3851.pdf).
- Main evidence: Section 7, **Blockwise-Columnar Storage**.
- Supporting material: Section 2 on architecture and transaction semantics, and Section 8 on production lessons.

What the paper establishes:

- Spanner reused significant Bigtable code, including its original on-disk format and block cache.
- The original format was robust, but its self-describing representation was redundant for small, schema-defined values.
- Traversing individual columns within a locality group was inefficient.
- Ressi retains an LSM-tree organization with periodic compaction.
- Blocks are organized in row-major order; values inside each block are organized in column-major order, essentially PAX.
- A multilevel index supports fast binary search for random key access.
- Parent and child rows can occupy the same or nearby blocks to support `INTERLEAVE IN PARENT`.
- Recent versions go into active files; older versions go into inactive files.
- Large, multipage values are separated into other files, so scans need not fetch them until needed.
- A vector is an ordinally indexed sequence of homogeneously typed values.
- A column can use one or more vectors within a block.
- Ressi can operate on vectors in compressed form.
- The paper describes a gradual, reversible migration using Spanner's existing data-movement mechanism.

Historical context: The paper describes Ressi entering production in the first half of 2017. This is a historical statement, not a current rollout status.

### S2. Spanner on a modern columnar storage engine

- [Google Cloud article](https://cloud.google.com/blog/products/databases/spanner-modern-columnar-storage-engine).
- This is the verified article corresponding to the blueprint's reference to migrating Spanner to Ressi. The initially inferred URL ending in `/migrating-spanner-to-ressi` returned 404 and is not a source.

What the article establishes:

- Spanner's original Bigtable-like SSTable stacks were not an ideal fit for its relational column-access patterns.
- Ressi was designed for distributed SQL with both OLTP and OLAP workloads, while maintaining and improving key-value read and write access.
- Optimizations include block layout, active/inactive file organization, and existence filters.
- Deployments, including Gmail on Spanner, showed improvements in CPU and storage I/O.
- The migration needed to preserve availability, data integrity, latency and throughput.
- Different workloads could regress even when the new format was better in aggregate.
- Compressibility differences could increase storage usage for outlier databases.
- Large-scale migration churn could expose latent failures.
- Mixed formats increased support complexity and performance variability.
- Database sizes varied substantially, so migration scheduling could not use one uniform policy.
- The team used reliability principles and automated candidate evaluation to flag unsuitable migration candidates for further examination.

No numerical CPU, I/O or compression improvement is attributed to Ressi in this carousel. The reviewed article supports qualitative improvements, not a universal percentage.

### S3. Spanner columnar engine overview

- [Google Cloud documentation](https://docs.cloud.google.com/spanner/docs/columnar-engine).
- This is the verified documentation path. Paths ending in `/columnar/overview` and `/columnar-engine/overview` returned 404 during research.

What the documentation establishes:

- Ressi's PAX layout groups column values within a block, but keeps the columns of nearby rows in that block to preserve efficient row access.
- The separate columnar engine dedicates runs of blocks to individual columns.
- This lets sequential scans read only the columns referenced by a query.
- The columnar representation is built in the background as part of compaction.
- Queries merge that representation with recent updates to provide strong consistency.
- Queries that do not benefit from columnar storage can continue to use PAX.
- Suitable workloads include operational reporting, served analytics and federated analytics.
- Large scans are the main target. Small scans and quickly satisfied `LIMIT` queries can favor row-oriented paths.
- Explicit column projection is important: `SELECT *` reads all columns.
- Query plans should be used to identify scan-bound workloads.
- Columnar read share reports how much a query reads from the columnar representation.
- High rates of updates or random inserts can affect performance. Append-only workloads have less impact.
- Columnar conversion of existing data happens asynchronously.
- The documentation identifies workload isolation as a separate concern and discusses Data Boost as analytical compute separation.
- The columnar representation adds storage usage and has storage-based billing.
- Spanner backups do not include the columnar format.
- The documentation advertises **up to 200x** scan improvement. This is an upper-bound product claim for the separate columnar engine, not a Ressi guarantee or a prediction for an arbitrary query.

### S4. Spanner columnar engine in preview

- [Google Cloud announcement](https://cloud.google.com/blog/products/databases/spanner-columnar-engine-in-preview).
- The reviewed announcement describes the engine as being in preview. Product availability is time-sensitive; use current documentation and account eligibility rather than treating the announcement as a permanent status statement.

What the announcement adds:

- Vectorized execution processes batches of values rather than processing each row separately.
- Large analytical scans can be directed to the columnar representation automatically.
- A major-compaction API can accelerate conversion of existing data.
- The article reports a single-node benchmark with speedups of 46.3x for a record count, 32.7x for aggregation with filtering, 46.7x for a high-selectivity scan, and 58.6x for a global aggregation.
- Those figures belong to that published benchmark. The carousel does not present them as general Ressi results.
- The article also covers serving curated Iceberg/lakehouse data in Spanner using reverse ETL, with integration discussions involving BigQuery, Databricks, Snowflake and Oracle.

The lakehouse integration material was reviewed for context. It is not necessary to explain Ressi's internal layout and was not added to the slides.

## Accuracy changes from the supplied blueprint

| Original implication | Treatment in the images |
|---|---|
| Google had to “throw out Bigtable's core storage format” | Spanner replaced its own inherited file format; Bigtable's format remains useful for Bigtable. |
| SSTables always pack a whole SQL row into one value | The row-serialized diagram is explicitly illustrative. SSTables are sorted key-value maps and can represent cells or locality groups. |
| SSTables necessarily decode every attribute for every query | Inefficient column traversal is supported; exact decoding behavior depends on serialization and access paths. |
| Ressi reads strictly the target column's bytes from disk | PAX improves in-block traversal and decoding. Column-only physical I/O is associated with the separate columnar engine; large-value separation and other Ressi optimizations can still save I/O. |
| Dictionary encoding and RLE are a confirmed Ressi codec list | They are shown as general examples enabled by homogeneous column data. The reviewed paper confirms compressed vectors but does not identify those specific codecs. |
| Compression always lowers replication cost | No blanket replication-cost claim is made. Spanner replicates log records, so smaller storage files do not by themselves establish lower consensus-log traffic. |
| Hybrid compaction always costs more than key-value merging | Encoding and rewriting have resource costs, but the net comparison is workload- and implementation-dependent. |
| Ressi eliminates every warehouse synchronization pipeline | It can reduce pipeline requirements for suitable operational reporting, not replace every warehouse or multi-source analytics workflow. |
| All columnar products have uniformly poor OLTP behavior | The landscape is framed as broad priorities, with product-specific semantics and latency left explicit. |
| Pure OLTP workloads should never use Ressi | The guidance concerns whether to build a custom hybrid engine, not whether a transactional application should use Spanner. |
| PAX provides strict serializability or MVCC by itself | The transaction system provides consistency; Ressi supports versioned physical storage without creating those guarantees on its own. |
| A 70/30 mix is a selection threshold | It is clearly labeled an illustration, not a decision rule. |
| Orders-of-magnitude gains apply to Ressi generally | The separate columnar engine and its scan-bound workload claims are distinguished from Ressi. |
| Blockwise-columnar storage is essential for every distributed SQL system | It is presented as a useful design choice, not a universal requirement. |

## Slide-by-slide details

### 1. Cover — SSTables to Ressi

**Message:** Spanner's storage evolved with its workload.

**Visual:** A split-screen comparison. On the left, sorted keys point to serialized values. On the right, a three-dimensional block contains vertically aligned column slices.

**Hook:** Why did a globally distributed SQL database outgrow its original file format?

**Context:** Spanner's earlier foundation was a reasonable engineering choice. It let the team focus on replication, distribution and scale before optimizing the physical representation for SQL.

### 2. The core problem — A key-value format, a relational workload

**Message:** Fast key access does not make column traversal efficient.

**Example:**

```sql
SELECT AVG(Age) FROM Users;
```

A row-serialized representation can force the engine to walk through data that the aggregate does not need. Decoding, parsing and memory traffic matter as well as disk access.

**Caveat:** This is an illustration of the mismatch, not proof that every SSTable implementation must decode every attribute. Indexes, locality groups, covering access paths and serialization details can change the work.

**Evidence:** S1 Section 7 and S2.

### 3. Enter Ressi — SQL-aware storage

**Message:** A storage representation should understand structured values, not merely carry opaque bytes.

Ressi combines typed vectors, a blockwise-columnar layout, sorted access paths and LSM compaction. It is not a move away from all LSM principles.

**Important detail:** A vector's ordinal identifies a position within a sequence of values of the same type. A block's columns can each contain one or more vectors.

**Evidence:** S1 Section 7.

### 4. SSTable anatomy — Sorted keys, serialized payloads

**Message:** SSTables provide an immutable, sorted-map structure. The key and value encoding controls relational efficiency.

**Conceptual teaching model:**

```text
Key 101 -> [Alice | 25 | Delhi]
Key 102 -> [Bob   | 30 | Mumbai]
Key 103 -> [Cara  | 28 | Delhi]
```

**Caveat:** This is not a literal dump of Spanner's former files. The original paper specifically discusses column traversal within locality groups. SSTable keys can carry cell-level information rather than only a primary row key.

**Evidence:** S1 Section 7.

### 5. Ressi anatomy — Rows per block, columns within it

**Message:** PAX preserves a nearby set of rows while grouping their attributes by column.

```text
Block
  UserID vector: [101, 102, 103]
  Name vector:   [Alice, Bob, Cara]
  Age vector:    [25, 30, 28]
```

A row lookup can find values in one block. A column operation can process a typed sequence rather than navigate interleaved row payloads.

**Additional detail:** Rows of interleaved child tables can stay in the same or nearby blocks as parent rows.

**Evidence:** S1 Section 7 and S3.

### 6. Query paths — Same key lookup, less scan decoding

**Point read:**

```sql
SELECT Name, Age FROM Users WHERE UserID = 102;
```

The conceptual paths are a key seek, a block access, and extraction of relevant values. Ressi's multilevel index preserves efficient random key access.

**Column scan:**

```sql
SELECT AVG(Age) FROM Users;
```

PAX lets the engine traverse Age vectors within blocks. This can reduce processing of unrelated values.

**Critical distinction:** Ressi still colocates multiple columns in a block. Do not infer that a physical block read fetches only Age. Dedicated columnar runs provide stronger column-level disk-read selectivity.

**Other Ressi I/O savings:** Segregating large values and separating current from older versions can avoid loading data that a query does not need.

**Evidence:** S1 Section 7 and S3.

### 7. Encoding and compression — Similar values, smaller representations

**Message:** Homogeneous types support type-aware encoding and compressed processing.

**General dictionary example:**

```text
Delhi, Mumbai, Delhi -> 0, 1, 0
Dictionary: 0 = Delhi, 1 = Mumbai
```

**General run-length example:**

```text
25, 25, 25, 30, 30 -> (25 x 3), (30 x 2)
```

These are educational examples, not a sourced assertion about Ressi's exact production codec menu. Actual compressibility depends on cardinality, ordering, types and distribution.

**Confirmed Ressi property:** The paper says it can operate directly on compressed vectors.

**Evidence:** S1 Section 7; S2 discusses improved compression in general and outliers.

### 8. The HTAP opportunity — One data model, two access patterns

**Message:** A shared operational dataset can support both transaction-oriented access and analytics.

OLTP examples include orders, payments and point reads. OLAP examples include reporting, aggregation and large scans.

Ressi is one part of making mixed workloads practical. Query execution, scheduling, compute isolation and transaction semantics also matter.

**Caveat:** Some operational reporting can avoid a separate pipeline. Historical, multi-source, transformation-heavy or independently governed analytics may still need a warehouse.

**Evidence:** S1, S2 and S3. The warehouse qualification is architectural guidance, not a vendor guarantee.

### 9. Alternatives — Different engines, different priorities

**LSM-oriented systems:** RocksDB and Cassandra are familiar examples of systems built around sorted, merge-oriented storage. Their APIs and database semantics are different; this grouping is not a claim of identical behavior.

**Analytical columnar systems:** ClickHouse and Snowflake favor analytical scans and aggregation. Their transaction features and update behavior must be assessed individually.

**Hybrid layouts:** PAX/Ressi keep row locality while making columns contiguous inside a block.

**Important distinction:** LSM describes organization and merging of sorted data. Row-oriented, blockwise-columnar and columnar describe physical layouts. Ressi is an LSM system with a PAX-like layout.

The named-product comparison is broad contextual guidance. No product benchmarks or current feature-by-feature audit were performed.

### 10. Hidden complexity — The hybrid is useful, not free

**Version management:** Recent and older values occupy different files in Ressi.

**Compaction:** Background sorting, encoding and rewriting consume resources. This does not prove that every hybrid is more expensive than every row-oriented format.

**Wide rows:** Fetching every attribute can require accessing several vectors. The benefit of narrow projection may be smaller for `SELECT *`.

**Migration:** Mixed formats, workload outliers, data integrity checks and reversible conversion deserve as much attention as the new format.

**Evidence:** S1 Section 7 and S2. Wide-row reconstruction and encoding-cost discussion are general design considerations, not measured Ressi regressions.

### 11. When not to build it — Do you need a hybrid layout?

Consider a simpler design if:

- Values are opaque and never projected or analyzed.
- Embedded-resource limits dominate the problem.
- Indexed point access already meets the workload requirements.
- There is no measured scan or decoding bottleneck.

**Caveat:** These are custom-engine design heuristics. They do not imply that Spanner is unsuitable for OLTP-only applications, or that PAX cannot benefit them.

### 12. Long-term benefits — Less wasted work, fewer moving parts

Suitable operational reports can run closer to live data. A SQL-aware storage representation gives the engine a more efficient foundation.

S2 reports improvements in CPU and storage I/O, including deployments with Gmail. It does not establish a universal percentage.

**Consistency boundary:** Spanner's transaction system supplies external consistency and snapshot behavior. Ressi stores the versions required by that system; its layout alone does not create serializability.

**Evidence:** S1 Sections 2 and 7; S2.

### 13. Ressi meets a dedicated columnar engine

**Message:** PAX is a useful compromise, not a pure column store.

Ressi groups columns within each block. The separate Spanner columnar engine groups runs of blocks by column.

```text
Background-built columnar representation
                 +
Recent transactional updates
                 |
                 v
       Consistent query snapshot
```

The columnar representation is built during compaction. Query-time reconciliation with recent updates maintains strong consistency. Queries that do not benefit can continue to use PAX.

**Operational caveats:** The extra representation consumes storage; coverage takes time to build; high churn can affect benefits; backups do not include the columnar format.

**Performance qualification:** The documentation's “up to 200x” applies to scan performance with the columnar engine. It is not a guarantee for all analytics, joins or Ressi point reads.

**Evidence:** S3 and S4.

### 14. Actionable takeaways — Measure, then choose

Start with a real query plan and a representative dataset.

1. Identify whether the bottleneck is scanning, decoding, I/O, joins, contention or something else.
2. Project only the columns needed by the query.
3. Use type-aware representations for structured data.
4. Benchmark narrow scans and full-row reads.
5. Check point-read and write latency while compaction runs.
6. For the separate columnar engine, inspect columnar read share and added storage.

**70/30 qualification:** Counting queries is not sufficient. A few scans can consume most resources. The mix shown in the slide is only a visual example.

**Evidence:** S3 supplies the query-plan, projection and coverage guidance. The wider benchmarking checklist is engineering guidance.

### 15. Conclusion and CTA

**Summary:** SSTables supplied a robust key-value foundation. Ressi improved Spanner's fit for structured distributed SQL by combining sorted access, typed vectors and blockwise-columnar storage.

**Engagement:** What storage engine powers your core microservices? Drop your architecture stack in the comments.

**Follow:** Save this deep dive and follow @engineering.by.heart.

**Final principle:** Reduce work per query without losing the guarantees the application needs.

## Migration details reviewed beyond the slide copy

The original paper describes changing a group's per-replica storage-format specification, then moving data from the old group to a new group. The old group continues to serve live traffic during copying. When the new group is ready, it takes over.

The mechanism supports new-format groups, mixed-format groups for testing, and reversal to SSTables. The paper emphasizes gradual rollout to reduce disruption.

The Cloud article adds production-scale safeguards: assess candidate health and suitability, control exposure, monitor performance and integrity, and account for ongoing ambient changes. Success with one database does not prove safety for another.

These points explain why storage migration is not merely rewriting bytes on disk. Control-plane automation, workload monitoring and rollback are part of the design.

## Research scope and limitations

- Primary sources were used for Ressi architecture and Spanner's separate columnar engine.
- The paper was downloaded and its storage section was read directly.
- The Cloud migration article, columnar overview and preview announcement were read.
- Web search was used to locate sources; the search-generated summaries were not treated as authoritative when they contradicted a fetched URL or primary text.
- Several inferred URLs returned 404; the verified replacement URLs appear above.
- The research did not establish Ressi's exact production codec list, universal compaction overhead, exact compression ratios, or quantified replication-cost savings.
- No direct benchmark of Spanner, RocksDB, Cassandra, ClickHouse or Snowflake was run.
- All diagrams are original teaching illustrations, not official implementation schematics.
- No Adobe, Google or third-party logo or scraped illustration is embedded.
- Product availability, pricing and performance claims can change. Recheck the linked current documentation before turning this educational carousel into procurement guidance.
