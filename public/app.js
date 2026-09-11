const state = {
  step: 0,
  steps: [
    {
      kicker: "01 · Agent intent",
      title: "The agent proposes a publication",
      copy: "The agent can prepare an exact destination and exact text. It does not receive unchecked social-account authority.",
      log: ["intent.received", "destination=threads", "content.digest=7e81…", "effect=not-authorised"]
    },
    {
      kicker: "02 · Owner review",
      title: "A human sees the exact effect first",
      copy: "PostSteward freezes the review inputs so the approved destination and copy cannot silently drift between review and execution.",
      log: ["review.created", "destination.locked=true", "content.locked=true", "approval=required"]
    },
    {
      kicker: "03 · Escape hatch",
      title: "Approval still has a cancellation boundary",
      copy: "The canonical owner journey includes a thirty-second cancellation window before dispatch. The showcase only demonstrates the state transition.",
      log: ["approval.recorded", "cancel.window=30s", "provider.write=pending", "simulation=true"]
    },
    {
      kicker: "04 · Durable write",
      title: "The provider write is treated as an external effect",
      copy: "PostSteward reserves publication durably and does not blindly retry an uncertain write. That is the difference between automation and accountable automation.",
      log: ["reservation=durable", "write.intent=fenced", "blind.retry=false", "provider=canonical-service-only"]
    },
    {
      kicker: "05 · Independent readback",
      title: "A receipt is not the same as verification",
      copy: "After the provider returns an identifier, PostSteward separately reads the published object back and checks the durable identity and exact content where the provider supports it.",
      log: ["provider.id=durable", "readback=separate", "receipt=inspectable", "verified≠assumed"]
    }
  ]
};

const byId = (id) => document.getElementById(id);
const stepKicker = byId("step-kicker");
const stepTitle = byId("step-title");
const stepCopy = byId("step-copy");
const stepLog = byId("step-log");
const stepIndex = byId("step-index");
const prevButton = byId("step-prev");
const nextButton = byId("step-next");

function escapeHtml(value) {
  return value.replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;"
  }[char]));
}

function renderStep() {
  const step = state.steps[state.step];
  stepKicker.textContent = step.kicker;
  stepTitle.textContent = step.title;
  stepCopy.textContent = step.copy;
  stepIndex.textContent = `${state.step + 1} / ${state.steps.length}`;
  stepLog.replaceChildren(...step.log.map((line, index) => {
    const row = document.createElement("li");
    row.innerHTML = `<span>${String(index + 1).padStart(2, "0")}</span><code>${escapeHtml(line)}</code>`;
    return row;
  }));
  prevButton.disabled = state.step === 0;
  nextButton.textContent = state.step === state.steps.length - 1 ? "Restart walkthrough" : "Next control";
}

prevButton.addEventListener("click", () => {
  state.step = Math.max(0, state.step - 1);
  renderStep();
});

nextButton.addEventListener("click", () => {
  state.step = state.step === state.steps.length - 1 ? 0 : state.step + 1;
  renderStep();
});

async function loadEvidence() {
  const target = byId("evidence-grid");
  const revision = byId("canonical-revision");
  try {
    const response = await fetch("./evidence.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`Evidence unavailable (${response.status})`);
    const evidence = await response.json();
    revision.textContent = evidence.canonicalRevision.slice(0, 8);
    revision.href = `${evidence.canonicalRepository}/commit/${evidence.canonicalRevision}`;
    target.replaceChildren(...evidence.facts.map((fact) => {
      const card = document.createElement("article");
      card.className = "evidence-card";
      const stateLabel = fact.state === "verified" ? "Verified" : "Open gate";
      card.innerHTML = `
        <div class="evidence-state evidence-state--${fact.state}">${stateLabel}</div>
        <p>${escapeHtml(fact.label)}</p>
        <strong>${escapeHtml(fact.value)}</strong>
        <a href="${fact.evidence}" target="_blank" rel="noreferrer">Inspect evidence <span aria-hidden="true">↗</span></a>
      `;
      return card;
    }));
  } catch {
    target.innerHTML = `<p class="evidence-error">Evidence panel could not load. Use the canonical repository links instead.</p>`;
  }
}

renderStep();
loadEvidence();
