"""Generate a natural-language insight for a completed analysis job via Claude."""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.graph import CentralityResult, GraphNode, GraphResult, GraphType
from app.models.author import Author
from app.models.keyword import Keyword
from app.models.paper import Paper

logger = logging.getLogger(__name__)

_MAX_ITEMS = 5
_MAX_KW = 10


def _top_papers(db: Session, graph: GraphResult) -> list[str]:
    stmt = (
        select(Paper.title, CentralityResult.pagerank)
        .join(GraphNode, GraphNode.paper_id == Paper.id)
        .join(CentralityResult, CentralityResult.node_id == GraphNode.id)
        .where(GraphNode.graph_id == graph.id)
        .where(CentralityResult.pagerank.isnot(None))
        .order_by(CentralityResult.pagerank.desc())
        .limit(_MAX_ITEMS)
    )
    return [row[0] for row in db.execute(stmt) if row[0]]


def _top_authors(db: Session, graph: GraphResult) -> list[str]:
    stmt = (
        select(Author.name, CentralityResult.pagerank)
        .join(GraphNode, GraphNode.author_id == Author.id)
        .join(CentralityResult, CentralityResult.node_id == GraphNode.id)
        .where(GraphNode.graph_id == graph.id)
        .where(CentralityResult.pagerank.isnot(None))
        .order_by(CentralityResult.pagerank.desc())
        .limit(_MAX_ITEMS)
    )
    return [row[0] for row in db.execute(stmt) if row[0]]


def _top_keywords(db: Session, graph: GraphResult) -> list[str]:
    stmt = (
        select(Keyword.display, CentralityResult.weighted_degree)
        .join(GraphNode, GraphNode.keyword_id == Keyword.id)
        .join(CentralityResult, CentralityResult.node_id == GraphNode.id)
        .where(GraphNode.graph_id == graph.id)
        .where(CentralityResult.weighted_degree.isnot(None))
        .order_by(CentralityResult.weighted_degree.desc())
        .limit(_MAX_KW)
    )
    return [row[0] for row in db.execute(stmt) if row[0]]


def _build_prompt(
    keyword: str,
    year_start: int | None,
    year_end: int | None,
    papers_processed: int,
    graphs: dict[str, GraphResult],
    top_papers: list[str],
    top_authors: list[str],
    top_keywords: list[str],
) -> str:
    year_range = (
        f"{year_start}–{year_end}"
        if year_start and year_end
        else (str(year_start) + "–현재" if year_start else "전체 기간")
    )
    pg = graphs.get("paper")
    ag = graphs.get("author")
    kg = graphs.get("keyword")

    lines = [
        f'다음은 "{keyword}" 키워드로 수집·분석된 글로벌 학술 연구 네트워크 데이터입니다.',
        f"분석 기간: {year_range} / 논문 수: {papers_processed:,}편",
        "",
    ]
    if pg:
        lines += [
            "## 논문 인용 네트워크",
            f"- 노드(논문) {pg.node_count:,}개 / 엣지(인용) {pg.edge_count:,}개 / 군집 {pg.cluster_count}개",
        ]
        if top_papers:
            lines.append("- 영향력 상위 논문(PageRank 기준):")
            for i, t in enumerate(top_papers, 1):
                lines.append(f"  {i}. {t}")
        lines.append("")
    if ag:
        lines += [
            "## 저자 공동연구 네트워크",
            f"- 노드(저자) {ag.node_count:,}개 / 엣지(공동논문) {ag.edge_count:,}개 / 군집 {ag.cluster_count}개",
        ]
        if top_authors:
            lines.append("- 핵심 저자(PageRank 기준):")
            for i, n in enumerate(top_authors, 1):
                lines.append(f"  {i}. {n}")
        lines.append("")
    if kg:
        lines += [
            "## 키워드 공동출현 네트워크",
            f"- 노드(키워드) {kg.node_count:,}개 / 엣지(동시등장) {kg.edge_count:,}개 / 군집 {kg.cluster_count}개",
        ]
        if top_keywords:
            lines.append(f"- 주요 키워드: {', '.join(top_keywords)}")
        lines.append("")
    lines += [
        "---",
        "위 데이터를 바탕으로 이 연구 분야의 특성을 한국어 3~5문단으로 분석해주세요.",
        "다음 관점을 포함하세요:",
        "1. 이 분야의 전반적인 연구 규모와 성숙도",
        "2. 주요 연구 흐름 또는 세부 주제 군집",
        "3. 핵심 저자·그룹의 특징 (가능한 경우)",
        "4. 주목할 만한 키워드 트렌드",
        "숫자나 목록 없이, 읽기 쉬운 분석 산문으로 작성하세요.",
    ]
    return "\n".join(lines)


def generate_insight(db: Session, job_id: uuid.UUID) -> str | None:
    """Return an LLM-generated insight string via Groq, or None if skipped/failed."""
    if not settings.groq_api_key:
        logger.info("GROQ_API_KEY not set — skipping insight generation")
        return None

    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai package not installed — skipping insight generation")
        return None

    stmt = select(GraphResult).where(GraphResult.job_id == job_id)
    graph_rows = list(db.execute(stmt).scalars().all())
    graphs: dict[str, GraphResult] = {g.graph_type: g for g in graph_rows}

    if not graphs:
        return None

    paper_g = graphs.get(GraphType.PAPER)
    author_g = graphs.get(GraphType.AUTHOR)
    keyword_g = graphs.get(GraphType.KEYWORD)

    top_papers = _top_papers(db, paper_g) if paper_g else []
    top_authors = _top_authors(db, author_g) if author_g else []
    top_keywords = _top_keywords(db, keyword_g) if keyword_g else []

    from app.models.job import AnalysisJob
    job = db.get(AnalysisJob, job_id)
    if not job:
        return None

    prompt = _build_prompt(
        keyword=job.keyword,
        year_start=job.year_start,
        year_end=job.year_end,
        papers_processed=job.papers_processed,
        graphs=graphs,
        top_papers=top_papers,
        top_authors=top_authors,
        top_keywords=top_keywords,
    )

    try:
        client = OpenAI(
            api_key=settings.groq_api_key,
            base_url=settings.insight_base_url,
        )
        response = client.chat.completions.create(
            model=settings.insight_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception:
        logger.exception("Groq insight generation failed for job %s", job_id)
        return None
