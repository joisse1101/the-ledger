import { useState } from "react";
import type { DecisionAnswer, PendingDecision } from "../../api/types";
import { QUESTION_TOOL } from "../../api/types";
import { buildAnswers, emptySelection, parseQuestions } from "../../lib/prompt";
import type { PromptQuestion, Selection } from "../../lib/prompt";

export interface DecisionPromptProps {
  decision: PendingDecision;
  /** True while an answer is on its way, so nothing can be sent twice. */
  busy: boolean;
  onAnswer: (answer: DecisionAnswer) => void;
}

/** A tool-permission prompt: the tool and its input, Approve, and Deny (which opens an optional reason). */
function PermissionPrompt({ decision, busy, onAnswer }: DecisionPromptProps) {
  const [denying, setDenying] = useState(false);
  const [reason, setReason] = useState("");

  const deny = () => {
    const trimmed = reason.trim();
    onAnswer(trimmed ? { decision: "deny", reason: trimmed } : { decision: "deny" });
  };

  return (
    <div className="detail-notice decision-card">
      <p className="detail-heading">Waiting for your decision</p>
      <p>
        <strong>{decision.tool_name}</strong>
      </p>
      <pre className="decision-input">{JSON.stringify(decision.tool_input, null, 2)}</pre>

      {denying ? (
        <>
          <label className="decision-reason">
            <span className="detail-caption">Reason for denying (optional)</span>
            <input
              type="text"
              value={reason}
              maxLength={200}
              autoFocus
              onChange={(event) => setReason(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !busy) deny();
              }}
            />
          </label>
          <div className="detail-actions">
            <button type="button" className="button button-danger" disabled={busy} onClick={deny}>
              {busy ? "Sending…" : "Confirm deny"}
            </button>
            <button type="button" className="button" disabled={busy} onClick={() => setDenying(false)}>
              Back
            </button>
          </div>
        </>
      ) : (
        <div className="detail-actions">
          <button type="button" className="button" disabled={busy} onClick={() => onAnswer({ decision: "allow" })}>
            {busy ? "Sending…" : "Approve"}
          </button>
          <button type="button" className="button button-danger" disabled={busy} onClick={() => setDenying(true)}>
            Deny
          </button>
        </div>
      )}
    </div>
  );
}

function QuestionField({
  promptId,
  index,
  question,
  selection,
  disabled,
  onChange,
}: {
  promptId: string;
  index: number;
  question: PromptQuestion;
  selection: Selection;
  disabled: boolean;
  onChange: (selection: Selection) => void;
}) {
  const type = question.multiSelect ? "checkbox" : "radio";
  const name = `${promptId}-${index}`;

  const toggle = (label: string, checked: boolean) => {
    if (question.multiSelect) {
      const picked = checked ? [...selection.picked, label] : selection.picked.filter((item) => item !== label);
      onChange({ ...selection, picked });
    } else {
      onChange({ ...selection, picked: [label], otherOn: false });
    }
  };

  return (
    <fieldset className="question" disabled={disabled}>
      <legend className="question-text">
        {question.header && <span className="question-header">{question.header}</span>}
        {question.question}
      </legend>
      {question.multiSelect && <p className="detail-caption">Choose any that apply.</p>}
      {question.options.map((option) => (
        <label key={option.label} className="question-option">
          <input
            type={type}
            name={name}
            checked={selection.picked.includes(option.label)}
            onChange={(event) => toggle(option.label, event.target.checked)}
          />
          <span>
            {option.label}
            {option.description && <span className="question-option-note">{option.description}</span>}
          </span>
        </label>
      ))}
      <label className="question-option">
        <input
          type={type}
          name={name}
          checked={selection.otherOn}
          onChange={(event) =>
            onChange(
              question.multiSelect
                ? { ...selection, otherOn: event.target.checked }
                : { picked: [], otherOn: event.target.checked, other: selection.other },
            )
          }
        />
        <span>Other</span>
      </label>
      {selection.otherOn && (
        <input
          type="text"
          className="question-other"
          aria-label={`Your own answer to: ${question.question}`}
          value={selection.other}
          maxLength={500}
          autoFocus
          onChange={(event) => onChange({ ...selection, other: event.target.value })}
        />
      )}
    </fieldset>
  );
}

/** An `AskUserQuestion` prompt: every question with its real options (several may be ticked where
 *  the question allows it) plus a free-text "Other". Send stays disabled until all are answered. */
function QuestionPrompt({ decision, busy, onAnswer, questions }: DecisionPromptProps & { questions: PromptQuestion[] }) {
  const [selections, setSelections] = useState<Selection[]>(() => questions.map(() => emptySelection));
  const answers = buildAnswers(questions, selections);

  return (
    <div className="detail-notice decision-card">
      <p className="detail-heading">Claude is asking you</p>
      {questions.map((question, index) => (
        <QuestionField
          key={index}
          promptId={decision.id}
          index={index}
          question={question}
          selection={selections[index]}
          disabled={busy}
          onChange={(next) => setSelections((current) => current.map((item, i) => (i === index ? next : item)))}
        />
      ))}
      <div className="detail-actions">
        <button
          type="button"
          className="button"
          disabled={busy || answers === null}
          onClick={() => answers && onAnswer({ decision: "answer", answers })}
        >
          {busy ? "Sending…" : "Send answer"}
        </button>
      </div>
    </div>
  );
}

/** Renders whichever kind of prompt this is. Give it `key={decision.id}` so a new prompt starts
 *  from a clean slate. */
export function DecisionPrompt(props: DecisionPromptProps) {
  if (props.decision.tool_name !== QUESTION_TOOL) return <PermissionPrompt {...props} />;

  const questions = parseQuestions(props.decision.tool_input);
  if (!questions) {
    return (
      <div className="detail-notice decision-card">
        <p className="detail-heading">Claude is asking you</p>
        <p>This question can't be answered from the dashboard - answer it in the terminal.</p>
        <pre className="decision-input">{JSON.stringify(props.decision.tool_input, null, 2)}</pre>
      </div>
    );
  }
  return <QuestionPrompt {...props} questions={questions} />;
}
