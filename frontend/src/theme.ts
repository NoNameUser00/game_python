import { createTheme } from '@uiw/codemirror-themes'
import { tags as t } from '@lezer/highlight'

/** Тёмная тема Dracula для редактора кода. */
export const draculaTheme = createTheme({
  theme: 'dark',
  settings: {
    background: '#282a36',
    foreground: '#f8f8f2',
    caret: '#f8f8f2',
    selection: '#44475a',
    selectionMatch: '#44475a',
    lineHighlight: '#343746',
    gutterBackground: '#282a36',
    gutterForeground: '#6272a4',
    gutterBorder: 'transparent',
    fontFamily: '"Fira Code", "JetBrains Mono", Menlo, Consolas, monospace',
    fontSize: '15px',
  },
  styles: [
    { tag: t.comment, color: '#6272a4', fontStyle: 'italic' },
    { tag: [t.string, t.special(t.string)], color: '#f1fa8c' },
    { tag: [t.number, t.bool, t.null, t.atom], color: '#bd93f9' },
    { tag: [t.keyword, t.modifier, t.operatorKeyword], color: '#ff79c6' },
    { tag: [t.operator, t.punctuation, t.separator, t.bracket], color: '#ff79c6' },
    { tag: [t.definition(t.variableName), t.function(t.variableName)], color: '#50fa7b' },
    { tag: [t.function(t.propertyName), t.typeName, t.className, t.namespace], color: '#8be9fd' },
    { tag: [t.propertyName, t.attributeName, t.labelName], color: '#66d9ef' },
    { tag: [t.tagName, t.angleBracket], color: '#ff79c6' },
    { tag: t.variableName, color: '#f8f8f2' },
    { tag: t.link, color: '#8be9fd', textDecoration: 'underline' },
    { tag: t.invalid, color: '#ff5555' },
  ],
})
