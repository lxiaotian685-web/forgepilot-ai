import { useEffect, useState } from "react";
import {
  ArrowRight24Regular,
  BookOpen24Regular,
  CheckmarkCircle24Regular,
  ClipboardTask24Regular,
  Copy24Regular,
  Database24Regular,
  Open24Regular,
  PeopleTeam24Regular,
  ShieldLock24Regular,
} from "@fluentui/react-icons";
import devicesScreenshot from "../../docs/screenshots/03-devices.png";
import diagnosisScreenshot from "../../docs/screenshots/05-diagnosis.png";
import ordersScreenshot from "../../docs/screenshots/07-work-orders.png";
import loginScreenshot from "../../docs/screenshots/01-login.png";
import overviewScreenshot from "../../docs/screenshots/02-overview.png";
import alertsScreenshot from "../../docs/screenshots/04-alerts.png";
import knowledgeScreenshot from "../../docs/screenshots/06-knowledge.png";
import peopleScreenshot from "../../docs/screenshots/08-people.png";
import auditScreenshot from "../../docs/screenshots/09-audit.png";

const githubUrl = "https://github.com/lxiaotian685-web/forgepilot-ai";
const videoUrl = "https://b23.tv/4HPzoyw";
const technicalDocUrl = "https://github.com/lxiaotian685-web/forgepilot-ai/releases/tag/v1.0.0";
const demoAccount = "demo@example.com";
const appRoot = import.meta.env.BASE_URL || "/";

const workflow = [
  ["设备建档与测点", "录入设备档案，关联运行测点与历史参数。"],
  ["知识库与来源引用", "上传技术资料，保留匹配片段与来源。"],
  ["AI 有据分析", "结合测点和证据形成初步分析与核验任务。"],
  ["现场核验工单", "现场人员按核验项检查并记录结果。"],
  ["主管验收与审计", "验收时更新设备状态，诊断随后确认。"],
];

const interfaceGallery = [
  [loginScreenshot, "登录与身份", "演示账号登录和组织身份入口"],
  [overviewScreenshot, "维护总览", "设备、告警和工单的统一概览"],
  [alertsScreenshot, "告警中心", "告警筛选、指派和状态流转"],
  [knowledgeScreenshot, "知识证据", "文档解析、切片和来源定位"],
  [peopleScreenshot, "人员与权限", "岗位、班组和成员状态管理"],
  [auditScreenshot, "审计记录", "关键业务操作的可追踪记录"],
];

const faq = [
  ["数据是真实工厂数据吗？", "不是。当前在线环境使用虚构演示数据，不代表真实工厂生产数据。"],
  ["AI 会直接控制设备吗？", "不会。系统不连接控制指令通道，AI 只提供带来源的初步分析和现场核验建议。"],
  ["证据不充分时会怎么处理？", "系统会标明证据不足或无法确认，并把缺失信息列入现场核验任务。"],
  ["设备状态如何更新？", "主管在工单验收时选择验收后的设备状态，系统同步更新并写入审计记录。"],
  ["人工巡检录入后图表会更新吗？", "会。批量录入成功后，最近测点和历史趋势会刷新，并与传感器来源分开标注。"],
  ["如何体验演示环境？", "点击进入在线演示，使用演示账号和登录页提供的密码即可体验。"],
];

function Brand() {
  return <a className="showcase-brand" href={appRoot} aria-label="ForgePilot 首页"><span>FP</span><strong>ForgePilot 制造领航</strong></a>;
}

function SectionHeading({ eyebrow, title, description }) {
  return <header className="showcase-section-heading">{eyebrow && <small>{eyebrow}</small>}<h2>{title}</h2>{description && <p>{description}</p>}</header>;
}

export default function ShowcasePage() {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const page = document.querySelector(".showcase-page");
    if (!page) return undefined;

    const revealItems = page.querySelectorAll(
      ".showcase-section-heading, .showcase-problem li, .workflow-track article, .showcase-screens figure, .boundary-columns article, .architecture-flow article, .showcase-faq details",
    );
    revealItems.forEach((item, index) => item.style.setProperty("--reveal-index", String(index % 5)));

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -8%" },
    );
    revealItems.forEach((item) => observer.observe(item));
    page.classList.add("is-motion-ready");

    const screenFigures = page.querySelectorAll(".showcase-screens figure");
    const cleanups = Array.from(screenFigures, (figure) => {
      const onMove = (event) => {
        const rect = figure.getBoundingClientRect();
        const x = (event.clientX - rect.left) / rect.width - 0.5;
        const y = (event.clientY - rect.top) / rect.height - 0.5;
        figure.style.setProperty("--screen-x", `${x * 7}deg`);
        figure.style.setProperty("--screen-y", `${y * -5}deg`);
        figure.style.setProperty("--shine-x", `${(x + 0.5) * 100}%`);
        figure.style.setProperty("--shine-y", `${(y + 0.5) * 100}%`);
      };
      const onLeave = () => {
        figure.style.setProperty("--screen-x", "0deg");
        figure.style.setProperty("--screen-y", "0deg");
      };
      figure.addEventListener("pointermove", onMove);
      figure.addEventListener("pointerleave", onLeave);
      return () => {
        figure.removeEventListener("pointermove", onMove);
        figure.removeEventListener("pointerleave", onLeave);
      };
    });
    return () => {
      observer.disconnect();
      cleanups.forEach((cleanup) => cleanup());
    };
  }, []);

  const copyAccount = async () => {
    await navigator.clipboard.writeText(demoAccount);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  };

  return <main className="showcase-page">
    <nav className="showcase-nav" aria-label="项目介绍导航">
      <Brand />
      <div className="showcase-nav-links">
        <a href="#problem">解决什么</a><a href="#workflow">如何工作</a><a href="#boundary">AI 边界</a><a href="#architecture">技术架构</a><a href="#faq">常见问题</a>
      </div>
      <div className="showcase-nav-actions"><a href={githubUrl} target="_blank" rel="noreferrer">GitHub</a><a className="showcase-button primary" href={appRoot}>进入在线演示</a></div>
    </nav>

    <section className="showcase-hero">
      <div className="showcase-hero-copy">
        <span className="showcase-kicker"><ShieldLock24Regular />有证据的工业设备维护协作平台</span>
        <h1>让设备诊断从经验判断，走向有证据、可复核、可追踪</h1>
        <p>连接设备数据、知识检索、AI 分析、人工核验与工单验收，构建责任闭环。</p>
        <div className="showcase-actions"><a className="showcase-button primary" href={appRoot}>进入在线演示</a><a className="showcase-button secondary" href="#workflow">查看业务闭环</a></div>
        <small className="showcase-demo-note">当前为虚构演示数据，不代表真实工厂生产数据。</small>
      </div>
      <figure className="showcase-hero-visual"><img src={diagnosisScreenshot} alt="ForgePilot 诊断工作台，展示证据引用和人工核验任务" /><figcaption><span>3 条引用证据</span><span>人工确认后才形成结论</span></figcaption></figure>
    </section>

    <section className="showcase-section showcase-problem" id="problem">
      <div><SectionHeading eyebrow="业务痛点与解决思路" title="传统运维断点与同一条可审计链路" /><ol><li><b>01</b><span><strong>设备与测点数据分散</strong>参数、时序测点和历史维修记录难以快速聚合。</span></li><li><b>02</b><span><strong>知识分散难以查验</strong>技术资料和检修手册难以快速定位对应章节。</span></li><li><b>03</b><span><strong>AI 缺乏来源证据</strong>没有资料引用的推断难以被技术人员复核。</span></li><li><b>04</b><span><strong>诊断与工单脱节</strong>分析结果不能直接转化为可执行和可验收的任务。</span></li></ol></div>
      <aside><h3>ForgePilot 方案</h3><p>让一次问题处理沿着同一条责任链推进。</p><div className="audit-chain"><span>设备与测点</span><ArrowRight24Regular /><span>知识引用</span><ArrowRight24Regular /><span>AI 初步分析</span><ArrowRight24Regular /><span>人工现场核验</span><ArrowRight24Regular /><span>工单验收</span><ArrowRight24Regular /><span>审计记录</span></div></aside>
    </section>

    <section className="showcase-section" id="workflow">
      <SectionHeading eyebrow="业务闭环" title="五步走完一次有据诊断" description="现场核验工单完成验收后，诊断才确认。" />
      <div className="workflow-track">{workflow.map(([title, text], index) => <article className={index === 2 ? "ai-step" : ""} key={title}><small>STEP {String(index + 1).padStart(2, "0")}</small><h3>{title}</h3><p>{text}</p>{index < workflow.length - 1 && <ArrowRight24Regular className="workflow-arrow" />}</article>)}</div>
    </section>

    <section className="showcase-section showcase-screens" id="screens">
      <SectionHeading eyebrow="真实系统界面" title="每一步都有可操作页面" description="以下均为当前在线版本的真实页面截图。" />
      <figure><div><small>设备档案与人工巡检</small><h3>设备中心与测点</h3><p>人工录入与传感器采集分开标注，录入后刷新历史趋势。</p></div><img src={devicesScreenshot} alt="ForgePilot 设备中心真实截图" /></figure>
      <figure className="reverse"><div><small>RAG 有据诊断</small><h3>诊断工作台与来源引用</h3><p>文档陈述、模型推断和待验证项分区展示，证据不足时不强行下结论。</p></div><img src={diagnosisScreenshot} alt="ForgePilot 诊断工作台真实截图" /></figure>
      <figure><div><small>现场核验与验收</small><h3>维护工单与状态流转</h3><p>现场核验结果进入工单，主管验收时选择设备状态并留下审计记录。</p></div><img src={ordersScreenshot} alt="ForgePilot 维护工单真实截图" /></figure>
    </section>

    <section className="showcase-section showcase-gallery" id="gallery">
      <SectionHeading eyebrow="完整界面画廊" title="其余页面一张不少" description="登录、总览、告警、知识、人员和审计页面均保留展示。" />
      <div className="showcase-gallery-grid">{interfaceGallery.map(([image, title, text]) => <figure key={title}><img src={image} alt={`ForgePilot ${title}真实截图`} loading="lazy" /><figcaption><strong>{title}</strong><span>{text}</span></figcaption></figure>)}</div>
    </section>

    <section className="showcase-section showcase-boundary" id="boundary">
      <SectionHeading eyebrow="人机协作防线" title="明确 AI 可信边界" description="技术人员始终是判断与责任主体。" />
      <div className="boundary-columns"><article><h3><CheckmarkCircle24Regular />AI 可以做</h3><ul><li>检索设备资料和相关文档切片</li><li>展示可核对的来源引用</li><li>形成有依据的初步分析建议</li><li>生成需要现场核验的任务项目</li></ul></article><article className="strict"><h3><ShieldLock24Regular />AI 坚决不做</h3><ul><li>不直接下发设备控制指令</li><li>不替代工程师作最终结论</li><li>无确凿证据时不编造结论</li><li>不跳过人工核验和主管验收</li></ul></article></div>
      <div className="boundary-timeline"><span>AI 初步分析</span><ArrowRight24Regular /><span>现场核验工单</span><ArrowRight24Regular /><span>人工核验</span><ArrowRight24Regular /><strong>主管工单验收</strong></div>
    </section>

    <section className="showcase-data-legend"><div><i className="sensor" /><strong>传感器采集</strong><span>网关接入的测点时序数据</span></div><div><i className="manual" /><strong>人工巡检</strong><span>现场批量录入并刷新趋势</span></div><div><i className="demo" /><strong>演示环境数据</strong><span>虚构数据，不代表真实生产数据</span></div></section>

    <section className="showcase-section showcase-architecture" id="architecture">
      <SectionHeading eyebrow="系统技术架构" title="分层模块与版本验证记录" description="模型密钥只保留在服务端，业务数据按组织和岗位授权。" />
      <div className="architecture-flow"><article><Database24Regular /><small>MODULE 01</small><h3>React 前端</h3><p>页面交互、工作台与趋势展示</p></article><ArrowRight24Regular /><article><ClipboardTask24Regular /><small>MODULE 02</small><h3>FastAPI 业务服务</h3><p>业务流程、令牌鉴权、岗位权限</p></article><ArrowRight24Regular /><article><BookOpen24Regular /><small>MODULE 03</small><h3>RAG 知识服务</h3><p>文档解析、切片检索、来源引用</p></article><ArrowRight24Regular /><article><ShieldLock24Regular /><small>MODULE 04</small><h3>DeepSeek</h3><p>服务端 API 调用，密钥不进浏览器</p></article></div>
      <div className="verification-record"><strong>当前版本验证记录</strong><span>92 项前端测试</span><span>86 项业务服务测试</span><span>132 项知识服务测试</span></div>
    </section>

    <section className="showcase-section showcase-faq" id="faq"><SectionHeading eyebrow="评审常见问题" title="常见问题与说明" />{faq.map(([question, answer], index) => <details key={question} open={index === 0}><summary>{question}</summary><p>{answer}</p></details>)}</section>

    <section className="showcase-cta"><div><h2>体验完整的设备诊断闭环</h2><p>从设备建档、知识检索和初步分析，一直走到现场核验与工单验收。</p><div className="showcase-actions"><a className="showcase-button light" href={appRoot}>进入在线演示</a><a className="showcase-button outline-light" href={githubUrl} target="_blank" rel="noreferrer">查看 GitHub</a><a href={videoUrl} target="_blank" rel="noreferrer">观看演示视频 <Open24Regular /></a><a href={technicalDocUrl} target="_blank" rel="noreferrer">下载技术文档 <Open24Regular /></a></div></div><div className="showcase-account"><small>演示账号</small><strong>{demoAccount}</strong><button type="button" onClick={copyAccount}><Copy24Regular />{copied ? "已复制" : "复制账号"}</button><span>演示密码请在登录页查看</span></div></section>

    <footer className="showcase-footer"><Brand /><span>© 2026 ForgePilot 制造领航</span><a href="https://beian.miit.gov.cn" target="_blank" rel="noreferrer">粤ICP备2026151829号-2</a></footer>
  </main>;
}
