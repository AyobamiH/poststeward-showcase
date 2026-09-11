const runButton = document.querySelector("#run-loop");
const agentSteps = [...document.querySelectorAll("#agent-steps li")];
const stories = [...document.querySelectorAll(".story")];
const log = document.querySelector("#agent-log");
const laneBadge = document.querySelector("#lane-badge");
const queueBadge = document.querySelector("#queue-badge");
const receiptBadge = document.querySelector("#receipt-badge");
const receiptStory = document.querySelector("#receipt-story");
const receiptResult = document.querySelector("#receipt-result");
const buildStatus = document.querySelector("#build-status");
const queueStatus = document.querySelector("#queue-status");
const laneStatus = document.querySelector("#lane-status");
const pipelineStatus = document.querySelector("#pipeline-status");

const messages = [
  "[CONTEXT] Agent read the current milestone and the reviewed GTM narrative.",
  "[STORY] Selected the developer context-switch problem because it is grounded in the current build story.",
  "[PREPARED] Destination and exact copy are fixed before the publishing boundary.",
  "[DISPATCH] Synthetic demo crossed the controlled publishing boundary. No real provider call was made.",
  "[RECEIPT] Demo outcome recorded. The developer never left the build to run this loop.",
];

let step = 0;

function render() {
  agentSteps.forEach((item, index) => {
    item.classList.toggle("done", index < step);
    item.classList.toggle("active", index === Math.min(step, agentSteps.length - 1));
  });

  stories.forEach((story, index) => {
    story.classList.toggle("selected", index === (step < 2 ? 0 : Math.min(step - 1, 2)));
  });

  log.textContent = step === 0
    ? "[READY] Agent can continue the GTM loop without pulling the developer out of the build."
    : messages[step - 1];

  laneBadge.textContent = step === 0 ? "IDLE" : step < 4 ? "RUNNING" : "CONTROLLED";
  queueBadge.textContent = step < 2 ? "READY" : "STORY SELECTED";
  receiptBadge.textContent = step < 5 ? "WAITING" : "RECORDED";
  receiptStory.textContent = step < 2 ? "not dispatched" : "Why building and marketing should not be serial jobs";
  receiptResult.textContent = step < 5 ? "awaiting agent step" : "synthetic provider outcome recorded";
  buildStatus.textContent = step === 0 ? "NEW MILESTONE" : "DEVELOPER BUILDING";
  queueStatus.textContent = step < 2 ? "3 GROUNDED" : "1 SELECTED";
  laneStatus.textContent = step === 0 ? "READY" : step < 5 ? "ACTIVE" : "COMPLETE";
  pipelineStatus.textContent = step < 5 ? "WARMING" : "STORY ADDED";
  runButton.textContent = step >= messages.length ? "Reset agent loop" : "Run next agent step";
}

runButton?.addEventListener("click", () => {
  if (step >= messages.length) step = 0;
  else step += 1;
  render();
});

render();
