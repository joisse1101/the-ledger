// Reading an `AskUserQuestion` prompt's `tool_input` and turning the user's picks back into the
// `answers` map the API expects ({"<question text>": label | free text | label[] for multi-select}).

export interface PromptOption {
  label: string;
  description: string;
}

export interface PromptQuestion {
  question: string;
  header: string;
  options: PromptOption[];
  multiSelect: boolean;
}

/** What the user has picked for one question so far. `other` is the free-text choice. */
export interface Selection {
  picked: string[];
  otherOn: boolean;
  other: string;
}

export const emptySelection: Selection = { picked: [], otherOn: false, other: "" };

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

/** The questions in an AskUserQuestion `tool_input`, or null when there is no readable question
 *  list (the server can't take a dashboard answer for such a prompt either; the terminal still can). */
export function parseQuestions(toolInput: Record<string, unknown>): PromptQuestion[] | null {
  const raw = toolInput.questions;
  if (!Array.isArray(raw) || raw.length === 0) return null;
  const questions: PromptQuestion[] = [];
  for (const item of raw) {
    if (typeof item !== "object" || item === null) return null;
    const entry = item as Record<string, unknown>;
    const question = text(entry.question);
    if (!question.trim()) return null;
    const options = (Array.isArray(entry.options) ? entry.options : []).flatMap((option): PromptOption[] => {
      if (typeof option !== "object" || option === null) return [];
      const label = text((option as Record<string, unknown>).label);
      return label ? [{ label, description: text((option as Record<string, unknown>).description) }] : [];
    });
    questions.push({ question, header: text(entry.header), options, multiSelect: entry.multiSelect === true });
  }
  return questions;
}

/** The answer for one question, or null while it isn't complete: a single-choice question needs one
 *  pick (or non-blank free text); a multi-select needs at least one, and free text, once ticked, must
 *  not be blank - the server refuses blank answers, so the UI never offers to send one. */
export function answerValue(question: PromptQuestion, selection: Selection): string | string[] | null {
  const other = selection.other.trim();
  if (selection.otherOn && !other) return null;
  if (question.multiSelect) {
    const values = selection.otherOn ? [...selection.picked, other] : selection.picked;
    return values.length > 0 ? values : null;
  }
  if (selection.otherOn) return other;
  return selection.picked.length === 1 ? selection.picked[0] : null;
}

/** The whole `answers` map, or null until every question has an answer. */
export function buildAnswers(
  questions: PromptQuestion[],
  selections: Selection[],
): Record<string, string | string[]> | null {
  const answers: Record<string, string | string[]> = {};
  for (const [index, question] of questions.entries()) {
    const value = answerValue(question, selections[index] ?? emptySelection);
    if (value === null) return null;
    answers[question.question] = value;
  }
  return answers;
}
