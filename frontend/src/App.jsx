import React, { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Container,
  Divider,
  FormControl,
  FormControlLabel,
  Grid,
  InputLabel,
  MenuItem,
  Paper,
  Radio,
  RadioGroup,
  Select,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Typography,
} from '@mui/material'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const DIMENSIONS = [
  { key: 'timeliness', label: 'Актуальность', description: 'Проверки своевременности доставки, свежести таблиц и корректности временных полей.' },
  { key: 'validity', label: 'Консистентность / допустимость', description: 'Проверки допустимых значений, диапазонов, форматов и регулярных выражений.' },
  { key: 'completeness', label: 'Полнота', description: 'Проверки NULL, пустых строк, условной обязательности и процента заполненности.' },
  { key: 'reasonableness', label: 'Разумность', description: 'Проверки аномалий количества строк и резкого роста доли NULL.' },
  { key: 'consistency', label: 'Согласованность', description: 'Проверки логических связей между полями и стабильности атрибутов сущности.' },
  { key: 'conformity', label: 'Соответствие', description: 'Проверки соответствия справочникам и доверенным источникам.' },
  { key: 'uniqueness', label: 'Уникальность', description: 'Проверки дублей, уникальности одного поля, комбинации полей и регистра.' },
  { key: 'integrity', label: 'Целостность', description: 'Проверки ссылочной целостности и обязательных связей между таблицами.' },
]

const WEEK_DAYS = [
  { value: 1, label: 'Понедельник' },
  { value: 2, label: 'Вторник' },
  { value: 3, label: 'Среда' },
  { value: 4, label: 'Четверг' },
  { value: 5, label: 'Пятница' },
  { value: 6, label: 'Суббота' },
  { value: 7, label: 'Воскресенье' },
]

function formatSchedule(config) {
  const type = config.schedule_type || 'manual'
  const time = config.schedule_time ? String(config.schedule_time).slice(0, 5) : ''
  if (type === 'manual') return 'Ручной запуск'
  if (type === 'interval') return `Каждые ${config.schedule_interval_minutes || '—'} мин.`
  if (type === 'daily') return `Ежедневно${time ? ` в ${time}` : ''}`
  if (type === 'weekly') {
    const day = WEEK_DAYS.find((item) => Number(item.value) === Number(config.schedule_day_of_week))?.label || 'день недели не задан'
    return `Еженедельно: ${day}${time ? ` в ${time}` : ''}`
  }
  if (type === 'monthly') return `Ежемесячно: ${config.schedule_day_of_month || '—'} числа${time ? ` в ${time}` : ''}`
  return type
}

const CHECK_HELP = {
  sla_delivery: {
    title: 'SLA доставки таблицы',
    text: 'Проверяет, была ли таблица актуализирована к ожидаемому времени доставки с допустимой погрешностью.',
    example: 'Ежедневно к 12:00, допустимое отклонение 3 часа, поле updated_at.',
  },
  table_freshness: {
    title: 'Последнее обновление таблицы',
    text: 'Проверяет максимальное значение временного поля в таблице и сравнивает его с допустимым возрастом данных.',
    example: 'updated_at должен быть не старше 24 часов.',
  },
  stale_status: {
    title: 'Зависший статус / задержка между событиями',
    text: 'Проверяет, что разница между двумя временными полями не больше заданного периода.',
    example: 'finished_at - started_at не больше 2 часов.',
  },
  future_timestamp: {
    title: 'Дата из будущего',
    text: 'Проверяет, что временное поле не содержит значений из будущего.',
    example: 'created_at не должен быть больше текущего времени.',
  },
  accepted_values: {
    title: 'Допустимые значения',
    text: 'Проверяет, что значение поля входит в заданный список.',
    example: 'country_code ∈ IE, US, FR, DE.',
  },
  numeric_range: {
    title: 'Числовой диапазон',
    text: 'Проверяет, что числовое значение находится между минимумом и максимумом.',
    example: 'age от 0 до 120.',
  },
  regex_match: {
    title: 'Регулярное выражение',
    text: 'Проверяет строковое значение на соответствие заданному шаблону.',
    example: 'email должен соответствовать базовому email regex.',
  },
  date_range: {
    title: 'Диапазон дат',
    text: 'Проверяет, что дата находится внутри допустимого интервала.',
    example: 'birth_date между 1900-01-01 и текущей датой.',
  },
  not_negative: {
    title: 'Неотрицательное значение',
    text: 'Проверяет нижнюю и, при необходимости, верхнюю границу числа.',
    example: 'price >= 0.',
  },
  not_null: {
    title: 'Отсутствие NULL',
    text: 'Проверяет, что выбранная колонка не содержит NULL.',
    example: 'customer_id не должен быть NULL.',
  },
  not_blank: {
    title: 'Отсутствие пустых строк',
    text: 'Проверяет, что поле не NULL и не пустая строка после trim.',
    example: 'email не должен быть пустым.',
  },
  conditional_not_null: {
    title: 'Условная полнота',
    text: 'Проверяет, что поле заполнено, если выполнено заданное условие.',
    example: 'Если country_code = IE, то email должен быть заполнен.',
  },
  expected_columns_present: {
    title: 'Наличие ожидаемых столбцов',
    text: 'Проверяет структуру таблицы через information_schema.',
    example: 'В таблице должны быть customer_id, email, updated_at.',
  },
  column_fill_rate: {
    title: 'Процент заполненности',
    text: 'Проверяет, что доля заполненных значений не ниже заданного процента.',
    example: 'email заполнен минимум у 95% строк.',
  },
  row_count_anomaly: {
    title: 'Аномалия количества строк',
    text: 'Сравнивает количество строк за текущий период с историческим уровнем.',
    example: 'За сегодня строк не меньше обычного уровня с отклонением до 50%.',
  },
  null_rate_anomaly: {
    title: 'Аномальный рост NULL',
    text: 'Сравнивает текущую долю NULL с исторической долей NULL.',
    example: 'null_rate(email) не должен вырасти больше чем на 20%.',
  },
  cross_field_comparison: {
    title: 'Сравнение двух полей',
    text: 'Проверяет логическое отношение между двумя полями в одной записи.',
    example: 'created_at <= updated_at.',
  },
  same_entity_same_attribute: {
    title: 'Стабильный атрибут сущности',
    text: 'Проверяет, что у одной сущности стабильный атрибут имеет одно значение.',
    example: 'У customer_id не должно быть разных birth_date.',
  },
  mutually_exclusive_fields: {
    title: 'Взаимоисключающие поля',
    text: 'Проверяет, что из группы полей заполнено не более одного.',
    example: 'person_inn и company_inn не должны быть заполнены одновременно.',
  },
  reference_match: {
    title: 'Соответствие справочнику',
    text: 'Проверяет, что значение существует в справочной таблице.',
    example: 'country_code должен существовать в demo.ref_country.country_code.',
  },
  unique: {
    title: 'Уникальность одного поля',
    text: 'Проверяет, что значения выбранной колонки не повторяются.',
    example: 'customer_id уникален.',
  },
  composite_unique: {
    title: 'Уникальность комбинации полей',
    text: 'Проверяет дубли по комбинации нескольких колонок.',
    example: 'order_id + product_id уникальны.',
  },
  duplicate_rows: {
    title: 'Полные дубликаты строк',
    text: 'Проверяет дубли по выбранному набору колонок.',
    example: 'Полностью одинаковые записи загрузки не допускаются.',
  },
  case_insensitive_unique: {
    title: 'Уникальность без учёта регистра',
    text: 'Проверяет уникальность после lower и trim.',
    example: 'Test@Mail.com и test@mail.com считаются дублем.',
  },
  foreign_key_exists: {
    title: 'Ссылочная целостность',
    text: 'Проверяет, что значение внешнего ключа существует в родительской таблице.',
    example: 'orders.customer_id есть в customers.customer_id.',
  },
  parent_has_child: {
    title: 'Наличие дочерних записей',
    text: 'Проверяет, что у каждой родительской записи есть хотя бы одна дочерняя.',
    example: 'У заказа должна быть хотя бы одна строка order_items.',
  },
  required_link_exists: {
    title: 'Обязательная связь',
    text: 'Проверяет наличие связанной записи при выполнении условия.',
    example: 'Если status = paid, должен существовать payment.',
  },
}

const PARAM_FIELDS = {
  sla_delivery: [
    { key: 'frequency', label: 'Частота доставки', type: 'select', options: ['daily', 'weekly', 'monthly'] },
    { key: 'delivery_time', label: 'Время доставки, HH:MM', type: 'text', placeholder: '12:00' },
    { key: 'tolerance_hours', label: 'Допустимое отклонение, часов', type: 'number', defaultValue: 3 },
    { key: 'timestamp_column', label: 'Поле последнего обновления', type: 'column' },
    { key: 'weekday', label: 'День недели для weekly, 1-7', type: 'number', optional: true },
    { key: 'day_of_month', label: 'День месяца для monthly', type: 'number', optional: true },
  ],
  table_freshness: [
    { key: 'timestamp_column', label: 'Поле последнего обновления', type: 'column' },
    { key: 'max_age_hours', label: 'Максимальный возраст, часов', type: 'number', defaultValue: 24 },
  ],
  stale_status: [
    { key: 'start_timestamp_column', label: 'Начальное временное поле', type: 'column' },
    { key: 'end_timestamp_column', label: 'Конечное временное поле', type: 'column' },
    { key: 'max_delay_hours', label: 'Максимальная разница, часов', type: 'number' },
  ],
  future_timestamp: [{ key: 'allowed_future_minutes', label: 'Допустимый лаг в будущее, минут', type: 'number', defaultValue: 0, optional: true }],
  accepted_values: [{ key: 'values', label: 'Допустимые значения через запятую', type: 'array', placeholder: 'IE, US, FR, DE' }],
  numeric_range: [
    { key: 'min_value', label: 'Минимальное значение', type: 'number' },
    { key: 'max_value', label: 'Максимальное значение', type: 'number' },
  ],
  regex_match: [{ key: 'pattern', label: 'Регулярное выражение', type: 'text' }],
  date_range: [
    { key: 'min_date', label: 'Минимальная дата', type: 'text', placeholder: '1900-01-01' },
    { key: 'max_date', label: 'Максимальная дата', type: 'text', placeholder: '2030-01-01' },
  ],
  not_negative: [
    { key: 'min_value', label: 'Нижняя граница', type: 'number', defaultValue: 0, optional: true },
    { key: 'max_value', label: 'Верхняя граница', type: 'number', optional: true },
  ],
  conditional_not_null: [
    { key: 'condition_column', label: 'Колонка условия', type: 'column' },
    { key: 'condition_operator', label: 'Оператор условия', type: 'select', options: ['=', '!=', '>', '>=', '<', '<=', 'in'] },
    { key: 'condition_value', label: 'Значение условия', type: 'text' },
  ],
  expected_columns_present: [{ key: 'required_columns', label: 'Ожидаемые колонки через запятую', type: 'array' }],
  column_fill_rate: [{ key: 'min_fill_percent', label: 'Минимальная заполненность, %', type: 'number', defaultValue: 95 }],
  row_count_anomaly: [
    { key: 'date_column', label: 'Поле даты', type: 'column' },
    { key: 'lookback_days', label: 'Глубина истории, дней', type: 'number', defaultValue: 14 },
    { key: 'max_deviation_percent', label: 'Допустимое отклонение, %', type: 'number', defaultValue: 50 },
  ],
  null_rate_anomaly: [
    { key: 'date_column', label: 'Поле даты', type: 'column' },
    { key: 'lookback_days', label: 'Глубина истории, дней', type: 'number', defaultValue: 14 },
    { key: 'max_increase_percent', label: 'Максимальный рост NULL, %', type: 'number', defaultValue: 20 },
  ],
  cross_field_comparison: [
    { key: 'left_column', label: 'Левая колонка', type: 'column' },
    { key: 'operator', label: 'Оператор', type: 'select', options: ['=', '!=', '>', '>=', '<', '<='] },
    { key: 'right_column', label: 'Правая колонка', type: 'column' },
  ],
  same_entity_same_attribute: [
    { key: 'entity_key_column', label: 'Ключ сущности', type: 'column' },
    { key: 'stable_attribute_column', label: 'Стабильный атрибут', type: 'column' },
  ],
  mutually_exclusive_fields: [{ key: 'columns', label: 'Взаимоисключающие колонки через запятую', type: 'array' }],
  reference_match: [
    { key: 'reference_schema', label: 'Схема справочника', type: 'text', defaultValue: 'demo' },
    { key: 'reference_table', label: 'Таблица справочника', type: 'text', defaultValue: 'ref_country' },
    { key: 'reference_column', label: 'Колонка справочника', type: 'text', defaultValue: 'country_code' },
  ],
  composite_unique: [{ key: 'columns', label: 'Колонки комбинации через запятую', type: 'array' }],
  duplicate_rows: [{ key: 'columns', label: 'Колонки для поиска дублей через запятую', type: 'array' }],
  foreign_key_exists: [
    { key: 'reference_schema', label: 'Родительская схема', type: 'text' },
    { key: 'reference_table', label: 'Родительская таблица', type: 'text' },
    { key: 'reference_column', label: 'Родительская колонка', type: 'text' },
  ],
  parent_has_child: [
    { key: 'parent_key_column', label: 'Ключ родителя', type: 'column' },
    { key: 'child_schema', label: 'Схема дочерней таблицы', type: 'text' },
    { key: 'child_table', label: 'Дочерняя таблица', type: 'text' },
    { key: 'child_key_column', label: 'Ключ дочерней таблицы', type: 'text' },
  ],
  required_link_exists: [
    { key: 'condition_column', label: 'Колонка условия', type: 'column' },
    { key: 'condition_operator', label: 'Оператор условия', type: 'select', options: ['=', '!=', '>', '>=', '<', '<='] },
    { key: 'condition_value', label: 'Значение условия', type: 'text' },
    { key: 'link_column', label: 'Колонка связи в текущей таблице', type: 'column' },
    { key: 'reference_schema', label: 'Схема связанной таблицы', type: 'text' },
    { key: 'reference_table', label: 'Связанная таблица', type: 'text' },
    { key: 'reference_column', label: 'Колонка связанной таблицы', type: 'text' },
  ],
}

function statusColor(status) {
  if (status === 'passed') return '#2e7d32'
  if (status === 'failed') return '#d32f2f'
  if (status === 'warning') return '#ed6c02'
  return '#90a4ae'
}

function StatusDot({ status }) {
  return <Box component="span" sx={{ display: 'inline-block', width: 12, height: 12, borderRadius: '50%', bgcolor: statusColor(status), mr: 1 }} />
}

function StatCard({ title, value, helper }) {
  return (
    <Card elevation={0} sx={{ border: '1px solid #dbe4f0' }}>
      <CardContent>
        <Typography variant="body2" color="text.secondary">{title}</Typography>
        <Typography variant="h4" sx={{ fontWeight: 800 }}>{value}</Typography>
        <Typography variant="caption" color="text.secondary">{helper}</Typography>
      </CardContent>
    </Card>
  )
}

function parseParamValue(field, value) {
  if (field.type === 'array') {
    return String(value || '').split(',').map((item) => item.trim()).filter(Boolean)
  }
  if (field.type === 'number') {
    if (value === '' || value === null || value === undefined) return undefined
    return Number(value)
  }
  return value
}

function isFieldRequired(field) {
  return !field.optional
}

function ParamField({ field, value, onChange, attributes }) {
  if (field.type === 'select') {
    return (
      <FormControl fullWidth required={isFieldRequired(field)}>
        <InputLabel>{field.label}</InputLabel>
        <Select value={value ?? ''} label={field.label} onChange={(e) => onChange(field.key, e.target.value)}>
          {field.options.map((option) => <MenuItem key={option} value={option}>{option}</MenuItem>)}
        </Select>
      </FormControl>
    )
  }
  if (field.type === 'column') {
    return (
      <FormControl fullWidth required={isFieldRequired(field)}>
        <InputLabel>{field.label}</InputLabel>
        <Select value={value ?? ''} label={field.label} onChange={(e) => onChange(field.key, e.target.value)}>
          {attributes.map((attribute) => <MenuItem key={attribute.attribute_id} value={attribute.column_name}>{attribute.column_name}</MenuItem>)}
        </Select>
      </FormControl>
    )
  }
  return (
    <TextField
      label={field.label}
      type={field.type === 'number' ? 'number' : 'text'}
      value={value ?? ''}
      onChange={(e) => onChange(field.key, e.target.value)}
      fullWidth
      required={isFieldRequired(field)}
      placeholder={field.placeholder}
    />
  )
}

export default function App() {
  const [role, setRole] = useState('admin')
  const [tab, setTab] = useState('setup')
  const [datasets, setDatasets] = useState([])
  const [attributes, setAttributes] = useState([])
  const [checkTypes, setCheckTypes] = useState([])
  const [notificationRules, setNotificationRules] = useState([])
  const [checkConfigs, setCheckConfigs] = useState([])
  const [dashboard, setDashboard] = useState(null)
  const [selectedSql, setSelectedSql] = useState(null)
  const [message, setMessage] = useState(null)
  const [apiError, setApiError] = useState(null)
  const [tableSearch, setTableSearch] = useState('')
  const [monitorDatasetId, setMonitorDatasetId] = useState('')
  const [setupDatasetId, setSetupDatasetId] = useState('')
  const [selectedDimension, setSelectedDimension] = useState('timeliness')
  const [selectedCheckCode, setSelectedCheckCode] = useState('')
  const [showHelpFor, setShowHelpFor] = useState(null)
  const [paramValues, setParamValues] = useState({})
  const [form, setForm] = useState({
    attribute_id: '',
    notification_rule_id: '',
    check_name: '',
    severity: 'warning',
    threshold_percent: '0',
    schedule_mode: 'manual',
    schedule_interval_minutes: '',
    schedule_time: '12:45',
    schedule_day_of_week: 1,
    schedule_day_of_month: 1,
    schedule_timezone: 'Europe/Moscow',
    filter_clause: '{"conditions":[]}',
  })

  async function fetchJson(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', 'X-User-Role': role, ...(options.headers || {}) },
      ...options,
    })
    if (!response.ok) {
      const payload = await response.json().catch(() => ({ detail: 'Unknown error' }))
      throw new Error(payload.detail || 'Request failed')
    }
    return response.json()
  }

  async function loadStatic() {
    const requests = await Promise.allSettled([
      fetchJson('/api/datasets'),
      fetchJson('/api/check-types'),
      fetchJson('/api/notification-rules'),
      fetchJson('/api/dashboard'),
    ])

    const [datasetsResult, checkTypesResult, notificationRulesResult, dashboardResult] = requests
    const rejected = requests.find((item) => item.status === 'rejected')

    if (datasetsResult.status === 'fulfilled') setDatasets(datasetsResult.value)
    if (checkTypesResult.status === 'fulfilled') setCheckTypes(checkTypesResult.value)
    if (notificationRulesResult.status === 'fulfilled') setNotificationRules(notificationRulesResult.value)
    if (dashboardResult.status === 'fulfilled') setDashboard(dashboardResult.value)

    if (rejected) {
      const text = rejected.reason?.message === 'Failed to fetch'
        ? 'Не удалось подключиться к backend API. Проверьте, что контейнер dq-backend запущен и http://localhost:8000/health открывается в браузере.'
        : rejected.reason?.message || 'Ошибка загрузки данных'
      setApiError(text)
      setMessage({ type: 'error', text })
    } else {
      setApiError(null)
    }
  }

  async function loadConfigs(datasetId = monitorDatasetId) {
    const query = datasetId ? `?dataset_id=${datasetId}&include_disabled=true` : '?include_disabled=true'
    const configs = await fetchJson(`/api/check-configs${query}`)
    setCheckConfigs(configs)
  }

  useEffect(() => {
    loadStatic().then(() => loadConfigs('').catch(() => null)).catch((error) => setMessage({ type: 'error', text: error.message }))
  }, [role])

  useEffect(() => {
    const datasetId = setupDatasetId || monitorDatasetId
    if (!datasetId) {
      setAttributes([])
      return
    }
    fetchJson(`/api/datasets/${datasetId}/attributes`).then(setAttributes).catch((error) => setMessage({ type: 'error', text: error.message }))
  }, [setupDatasetId, monitorDatasetId, role])

  useEffect(() => {
    if (monitorDatasetId) loadConfigs(monitorDatasetId).catch((error) => setMessage({ type: 'error', text: error.message }))
  }, [monitorDatasetId, role])

  const selectedCheckType = useMemo(() => checkTypes.find((item) => item.code === selectedCheckCode), [checkTypes, selectedCheckCode])
  const selectedDataset = useMemo(() => datasets.find((item) => String(item.dataset_id) === String(setupDatasetId)), [datasets, setupDatasetId])
  const monitorDataset = useMemo(() => datasets.find((item) => String(item.dataset_id) === String(monitorDatasetId)), [datasets, monitorDatasetId])
  const dimensionChecks = useMemo(() => checkTypes.filter((item) => item.dimension_name === selectedDimension), [checkTypes, selectedDimension])
  const filteredDatasets = useMemo(() => {
    const q = tableSearch.toLowerCase().trim()
    if (!q) return datasets
    return datasets.filter((dataset) => `${dataset.schema_name}.${dataset.table_name} ${dataset.display_name}`.toLowerCase().includes(q))
  }, [datasets, tableSearch])
  const tableConfigs = useMemo(() => checkConfigs.filter((config) => String(config.dataset_id) === String(monitorDatasetId)), [checkConfigs, monitorDatasetId])
  const tableSummary = useMemo(() => {
    const total = tableConfigs.length
    const active = tableConfigs.filter((item) => item.is_enabled).length
    const failed = tableConfigs.filter((item) => item.last_result_status === 'failed').length
    const passed = tableConfigs.filter((item) => item.last_result_status === 'passed').length
    const notRun = tableConfigs.filter((item) => item.last_result_status === 'not_run').length
    return { total, active, failed, passed, notRun }
  }, [tableConfigs])

  function updateParam(key, value) {
    setParamValues((prev) => ({ ...prev, [key]: value }))
  }

  function handleCheckSelect(code) {
    setSelectedCheckCode(code)
    const fields = PARAM_FIELDS[code] || []
    const defaults = {}
    fields.forEach((field) => {
      if (field.defaultValue !== undefined) defaults[field.key] = String(field.defaultValue)
    })
    setParamValues(defaults)
    const checkType = checkTypes.find((item) => item.code === code)
    setForm((prev) => ({ ...prev, attribute_id: '', check_name: checkType ? checkType.name : '' }))
  }

  async function handleCreateConfig(event) {
    event.preventDefault()
    if (role !== 'admin') return
    try {
      if (!setupDatasetId || !selectedCheckType) throw new Error('Выберите таблицу и тип проверки')
      if (selectedCheckType.level_scope === 'column' && !form.attribute_id) throw new Error('Для column-level проверки нужно выбрать атрибут')
      const fields = PARAM_FIELDS[selectedCheckType.code] || []
      const params = {}
      for (const field of fields) {
        const rawValue = paramValues[field.key]
        if (isFieldRequired(field) && (rawValue === undefined || rawValue === null || rawValue === '')) {
          throw new Error(`Заполните поле: ${field.label}`)
        }
        const parsed = parseParamValue(field, rawValue)
        if (parsed !== undefined && parsed !== '') params[field.key] = parsed
      }
      const scheduleType = form.schedule_mode
      if (scheduleType === 'interval' && Number(form.schedule_interval_minutes || 0) <= 0) {
        throw new Error('Для интервального запуска укажите положительный интервал в минутах')
      }
      if (['daily', 'weekly', 'monthly'].includes(scheduleType) && !form.schedule_time) {
        throw new Error('Для выбранной регулярности укажите время запуска')
      }
      if (scheduleType === 'weekly' && !form.schedule_day_of_week) {
        throw new Error('Для еженедельного запуска выберите день недели')
      }
      if (scheduleType === 'monthly' && (!form.schedule_day_of_month || Number(form.schedule_day_of_month) < 1 || Number(form.schedule_day_of_month) > 31)) {
        throw new Error('Для ежемесячного запуска укажите день месяца от 1 до 31')
      }

      const payload = {
        dataset_id: Number(setupDatasetId),
        attribute_id: selectedCheckType.level_scope === 'column' ? Number(form.attribute_id) : null,
        check_type_id: Number(selectedCheckType.check_type_id),
        notification_rule_id: form.notification_rule_id ? Number(form.notification_rule_id) : null,
        check_name: form.check_name || selectedCheckType.name,
        severity: form.severity,
        threshold_percent: Number(form.threshold_percent || 0),
        schedule_type: scheduleType,
        schedule_interval_minutes: scheduleType === 'interval' ? Number(form.schedule_interval_minutes) : null,
        schedule_time: ['daily', 'weekly', 'monthly'].includes(scheduleType) ? form.schedule_time : null,
        schedule_day_of_week: scheduleType === 'weekly' ? Number(form.schedule_day_of_week) : null,
        schedule_day_of_month: scheduleType === 'monthly' ? Number(form.schedule_day_of_month) : null,
        schedule_timezone: form.schedule_timezone || 'Europe/Moscow',
        params,
        filter_clause: JSON.parse(form.filter_clause || '{"conditions":[]}'),
        is_enabled: true,
      }
      await fetchJson('/api/check-configs', { method: 'POST', body: JSON.stringify(payload) })
      setMessage({ type: 'success', text: 'Проверка создана' })
      setParamValues({})
      setForm((prev) => ({ ...prev, check_name: '', attribute_id: '', schedule_interval_minutes: '', schedule_time: '12:45', schedule_day_of_week: 1, schedule_day_of_month: 1, threshold_percent: '0' }))
      await loadConfigs(monitorDatasetId)
    } catch (error) {
      setMessage({ type: 'error', text: error.message })
    }
  }

  async function handleRunCheck(checkConfigId) {
    try {
      const payload = await fetchJson(`/api/check-configs/${checkConfigId}/run`, { method: 'POST' })
      const status = payload.result?.status || payload.run.status
      setMessage({ type: status === 'failed' ? 'warning' : 'success', text: `Запуск завершён: ${status}` })
      if (payload.run?.executed_sql) {
        const config = checkConfigs.find((item) => item.check_config_id === checkConfigId)
        setSelectedSql({ title: config?.check_name || 'SQL-запрос проверки', sql: payload.run.executed_sql })
      }
      await loadConfigs(monitorDatasetId)
      setDashboard(await fetchJson('/api/dashboard'))
    } catch (error) {
      setMessage({ type: 'error', text: error.message })
    }
  }

  async function handleToggleEnabled(config) {
    const next = !config.is_enabled
    const ok = window.confirm(next ? 'Включить проверку?' : 'Отключить проверку? История результатов будет сохранена.')
    if (!ok) return
    try {
      await fetchJson(`/api/check-configs/${config.check_config_id}/enabled`, { method: 'PATCH', body: JSON.stringify({ is_enabled: next }) })
      setMessage({ type: 'success', text: next ? 'Проверка включена' : 'Проверка отключена' })
      await loadConfigs(monitorDatasetId)
    } catch (error) {
      setMessage({ type: 'error', text: error.message })
    }
  }

  async function handleShowSql(config) {
    try {
      if (config.last_executed_sql) {
        setSelectedSql({ title: config.check_name, sql: config.last_executed_sql })
        return
      }
      if (!config.last_run_id) {
        setMessage({ type: 'info', text: 'У этой проверки пока нет выполненного SQL-запроса. Запустите проверку вручную или дождитесь планового запуска.' })
        return
      }
      const result = await fetchJson(`/api/results/${config.last_run_id}`)
      setSelectedSql({ title: config.check_name, sql: result.executed_sql || 'SQL-запрос не найден для последнего запуска.' })
    } catch (error) {
      setMessage({ type: 'error', text: error.message })
    }
  }

  async function copySqlToClipboard() {
    if (!selectedSql?.sql) return
    try {
      await navigator.clipboard.writeText(selectedSql.sql)
      setMessage({ type: 'success', text: 'SQL-запрос скопирован' })
    } catch {
      setMessage({ type: 'warning', text: 'Не удалось скопировать автоматически. Выделите SQL вручную.' })
    }
  }

  function renderSetup() {
    return (
      <Stack spacing={3}>
        <Card elevation={0} sx={{ border: '1px solid #dbe4f0' }}>
          <CardContent>
            <Typography variant="h5" sx={{ fontWeight: 700 }}>Настройка проверок</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Выберите таблицу, измерение качества данных и конкретную проверку. После заполнения параметров нажмите «Подтвердить».
            </Typography>
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Таблица</InputLabel>
                  <Select value={setupDatasetId} label="Таблица" onChange={(e) => setSetupDatasetId(e.target.value)}>
                    {datasets.map((dataset) => (
                      <MenuItem key={dataset.dataset_id} value={dataset.dataset_id}>{dataset.display_name} ({dataset.schema_name}.{dataset.table_name})</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={6}>
                <Paper variant="outlined" sx={{ p: 2, bgcolor: '#f8fafc' }}>
                  <Typography sx={{ fontWeight: 700 }}>{selectedDataset ? selectedDataset.display_name : 'Таблица не выбрана'}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {selectedDataset ? `${selectedDataset.schema_name}.${selectedDataset.table_name} · owner: ${selectedDataset.owner_name || '—'} · criticality: ${selectedDataset.criticality}` : 'После выбора таблицы здесь появится краткая информация.'}
                  </Typography>
                </Paper>
              </Grid>
            </Grid>
          </CardContent>
        </Card>

        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', md: 'repeat(2, minmax(0, 1fr))', xl: 'repeat(4, minmax(0, 1fr))' },
            gap: 2,
            alignItems: 'stretch',
          }}
        >
          {DIMENSIONS.map((dimension) => (
            <Card
              key={dimension.key}
              onClick={() => { setSelectedDimension(dimension.key); setSelectedCheckCode('') }}
              elevation={0}
              sx={{
                height: 150,
                cursor: 'pointer',
                border: selectedDimension === dimension.key ? '2px solid #1565c0' : '1px solid #dbe4f0',
                display: 'flex',
              }}
            >
              <CardContent sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'flex-start' }}>
                <Typography sx={{ fontWeight: 800 }}>{dimension.label}</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>{dimension.description}</Typography>
              </CardContent>
            </Card>
          ))}
        </Box>

        <Grid container spacing={3}>
          <Grid item xs={12} lg={5}>
            <Card elevation={0} sx={{ border: '1px solid #dbe4f0' }}>
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>Проверки измерения</Typography>
                <Stack spacing={1.5}>
                  {dimensionChecks.map((check) => {
                    const help = CHECK_HELP[check.code] || { title: check.name, text: check.description, example: 'Заполните параметры согласно схеме.' }
                    return (
                      <Paper key={check.check_type_id} variant="outlined" sx={{ p: 2, borderColor: selectedCheckCode === check.code ? '#1565c0' : '#dbe4f0' }}>
                        <Stack direction="row" justifyContent="space-between" spacing={2} alignItems="center">
                          <Box>
                            <Typography sx={{ fontWeight: 700 }}>{check.name}</Typography>
                            <Typography variant="caption" color="text.secondary">code: {check.code} · {check.level_scope}</Typography>
                          </Box>
                          <Stack direction="row" spacing={1}>
                            <Button size="small" onClick={() => setShowHelpFor(showHelpFor === check.code ? null : check.code)}>Описание</Button>
                            <Button size="small" variant="contained" onClick={() => handleCheckSelect(check.code)}>Настроить</Button>
                          </Stack>
                        </Stack>
                        {showHelpFor === check.code && (
                          <Box sx={{ mt: 1.5, p: 1.5, borderRadius: 2, bgcolor: '#f8fafc' }}>
                            <Typography variant="body2"><b>{help.title}</b></Typography>
                            <Typography variant="body2" color="text.secondary">{help.text}</Typography>
                            <Typography variant="body2" sx={{ mt: 1 }}><b>Пример:</b> {help.example}</Typography>
                          </Box>
                        )}
                      </Paper>
                    )
                  })}
                </Stack>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} lg={7}>
            <Card elevation={0} sx={{ border: '1px solid #dbe4f0' }}>
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>Форма настройки проверки</Typography>
                {!selectedCheckType ? (
                  <Alert severity="info">Выберите проверку слева, чтобы открыть форму параметров.</Alert>
                ) : (
                  <Stack component="form" spacing={2} onSubmit={handleCreateConfig}>
                    <TextField label="Название проверки" value={form.check_name} onChange={(e) => setForm({ ...form, check_name: e.target.value })} fullWidth required />
                    {selectedCheckType.level_scope === 'column' && (
                      <FormControl fullWidth required>
                        <InputLabel>Атрибут</InputLabel>
                        <Select value={form.attribute_id} label="Атрибут" onChange={(e) => setForm({ ...form, attribute_id: e.target.value })}>
                          {attributes.map((attribute) => <MenuItem key={attribute.attribute_id} value={attribute.attribute_id}>{attribute.column_name}</MenuItem>)}
                        </Select>
                      </FormControl>
                    )}
                    <Grid container spacing={2}>
                      <Grid item xs={12} md={4}>
                        <FormControl fullWidth>
                          <InputLabel>Критичность</InputLabel>
                          <Select value={form.severity} label="Критичность" onChange={(e) => setForm({ ...form, severity: e.target.value })}>
                            <MenuItem value="info">info</MenuItem>
                            <MenuItem value="warning">warning</MenuItem>
                            <MenuItem value="critical">critical</MenuItem>
                          </Select>
                        </FormControl>
                      </Grid>
                      <Grid item xs={12} md={4}>
                        <TextField label="Порог ошибок, %" type="number" value={form.threshold_percent} onChange={(e) => setForm({ ...form, threshold_percent: e.target.value })} fullWidth />
                      </Grid>
                      <Grid item xs={12} md={4}>
                        <FormControl fullWidth>
                          <InputLabel>Уведомление</InputLabel>
                          <Select value={form.notification_rule_id} label="Уведомление" onChange={(e) => setForm({ ...form, notification_rule_id: e.target.value })}>
                            <MenuItem value="">Без уведомления</MenuItem>
                            {notificationRules.map((rule) => <MenuItem key={rule.notification_rule_id} value={rule.notification_rule_id}>{rule.email_to}</MenuItem>)}
                          </Select>
                        </FormControl>
                      </Grid>
                    </Grid>

                    <Paper variant="outlined" sx={{ p: 2 }}>
                      <Typography sx={{ fontWeight: 700, mb: 1 }}>Расписание запуска</Typography>
                      <RadioGroup row value={form.schedule_mode} onChange={(e) => setForm({ ...form, schedule_mode: e.target.value })}>
                        <FormControlLabel value="manual" control={<Radio />} label="Ручной" />
                        <FormControlLabel value="interval" control={<Radio />} label="Каждые N минут" />
                        <FormControlLabel value="daily" control={<Radio />} label="Ежедневно" />
                        <FormControlLabel value="weekly" control={<Radio />} label="Еженедельно" />
                        <FormControlLabel value="monthly" control={<Radio />} label="Ежемесячно" />
                      </RadioGroup>
                      {form.schedule_mode === 'interval' && (
                        <TextField sx={{ mt: 1 }} label="Интервал, минут" type="number" value={form.schedule_interval_minutes} onChange={(e) => setForm({ ...form, schedule_interval_minutes: e.target.value })} />
                      )}
                      {['daily', 'weekly', 'monthly'].includes(form.schedule_mode) && (
                        <Grid container spacing={2} sx={{ mt: 0.5 }}>
                          <Grid item xs={12} md={4}>
                            <TextField
                              label="Время запуска"
                              type="time"
                              value={form.schedule_time}
                              onChange={(e) => setForm({ ...form, schedule_time: e.target.value })}
                              fullWidth
                              InputLabelProps={{ shrink: true }}
                              helperText="Например: 12:45"
                            />
                          </Grid>
                          {form.schedule_mode === 'weekly' && (
                            <Grid item xs={12} md={4}>
                              <FormControl fullWidth>
                                <InputLabel>День недели</InputLabel>
                                <Select value={form.schedule_day_of_week} label="День недели" onChange={(e) => setForm({ ...form, schedule_day_of_week: e.target.value })}>
                                  {WEEK_DAYS.map((day) => <MenuItem key={day.value} value={day.value}>{day.label}</MenuItem>)}
                                </Select>
                              </FormControl>
                            </Grid>
                          )}
                          {form.schedule_mode === 'monthly' && (
                            <Grid item xs={12} md={4}>
                              <TextField
                                label="День месяца"
                                type="number"
                                value={form.schedule_day_of_month}
                                onChange={(e) => setForm({ ...form, schedule_day_of_month: e.target.value })}
                                fullWidth
                                inputProps={{ min: 1, max: 31 }}
                              />
                            </Grid>
                          )}
                          <Grid item xs={12} md={4}>
                            <TextField
                              label="Часовой пояс"
                              value={form.schedule_timezone}
                              onChange={(e) => setForm({ ...form, schedule_timezone: e.target.value })}
                              fullWidth
                              helperText="Например: Europe/Moscow"
                            />
                          </Grid>
                        </Grid>
                      )}
                    </Paper>

                    {(PARAM_FIELDS[selectedCheckType.code] || []).length > 0 && (
                      <Paper variant="outlined" sx={{ p: 2 }}>
                        <Typography sx={{ fontWeight: 700, mb: 2 }}>Параметры проверки</Typography>
                        <Grid container spacing={2}>
                          {(PARAM_FIELDS[selectedCheckType.code] || []).map((field) => (
                            <Grid item xs={12} md={6} key={field.key}>
                              <ParamField field={field} value={paramValues[field.key]} onChange={updateParam} attributes={attributes} />
                            </Grid>
                          ))}
                        </Grid>
                      </Paper>
                    )}

                    <TextField label="JSON фильтра" value={form.filter_clause} onChange={(e) => setForm({ ...form, filter_clause: e.target.value })} fullWidth multiline minRows={2} helperText='Например: {"conditions":[{"field":"country_code","operator":"=","value":"IE"}]}' />
                    <Button type="submit" variant="contained" size="large">Подтвердить</Button>
                  </Stack>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Stack>
    )
  }

  function renderMonitoring() {
    return (
      <Stack spacing={3}>
        <Card elevation={0} sx={{ border: '1px solid #dbe4f0' }}>
          <CardContent>
            <Typography variant="h5" sx={{ fontWeight: 800 }}>Мониторинг проверок</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>Сначала найдите и выберите таблицу, затем откроется список настроенных проверок и последних результатов.</Typography>
            <TextField sx={{ mt: 2 }} fullWidth label="Поиск таблицы" value={tableSearch} onChange={(e) => setTableSearch(e.target.value)} />
            <Grid container spacing={2} sx={{ mt: 0.5 }}>
              {filteredDatasets.map((dataset) => (
                <Grid item xs={12} md={6} lg={4} key={dataset.dataset_id}>
                  <Card onClick={() => setMonitorDatasetId(dataset.dataset_id)} elevation={0} sx={{ cursor: 'pointer', border: String(monitorDatasetId) === String(dataset.dataset_id) ? '2px solid #1565c0' : '1px solid #dbe4f0' }}>
                    <CardContent>
                      <Typography sx={{ fontWeight: 800 }}>{dataset.display_name}</Typography>
                      <Typography variant="body2" color="text.secondary">{dataset.schema_name}.{dataset.table_name}</Typography>
                      <Typography variant="caption" color="text.secondary">owner: {dataset.owner_name || '—'} · criticality: {dataset.criticality}</Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </CardContent>
        </Card>

        {monitorDataset && (
          <>
            <Grid container spacing={2}>
              <Grid item xs={12} md={3}><StatCard title="Всего проверок" value={tableSummary.total} helper={monitorDataset.display_name} /></Grid>
              <Grid item xs={12} md={3}><StatCard title="Активные" value={tableSummary.active} helper="is_enabled = true" /></Grid>
              <Grid item xs={12} md={3}><StatCard title="С ошибками" value={tableSummary.failed} helper="latest status = failed" /></Grid>
              <Grid item xs={12} md={3}><StatCard title="Не запускались" value={tableSummary.notRun} helper="нет результата" /></Grid>
            </Grid>

            <Card elevation={0} sx={{ border: '1px solid #dbe4f0' }}>
              <CardContent>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                  <Box>
                    <Typography variant="h6" sx={{ fontWeight: 800 }}>Проверки таблицы {monitorDataset.schema_name}.{monitorDataset.table_name}</Typography>
                    <Typography variant="body2" color="text.secondary">Для администратора доступны ручной запуск и отключение проверки.</Typography>
                  </Box>
                  <Button variant="outlined" onClick={() => loadConfigs(monitorDatasetId)}>Обновить</Button>
                </Stack>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Статус</TableCell>
                      <TableCell>Название проверки</TableCell>
                      <TableCell>Измерение</TableCell>
                      <TableCell>Время проверки</TableCell>
                      <TableCell>Ошибки</TableCell>
                      <TableCell>Активность</TableCell>
                      <TableCell>Действия</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {tableConfigs.map((config) => (
                      <TableRow key={config.check_config_id} sx={{ opacity: config.is_enabled ? 1 : 0.55 }}>
                        <TableCell><StatusDot status={config.last_result_status} />{config.last_result_status}</TableCell>
                        <TableCell>
                          <Typography sx={{ fontWeight: 700 }}>{config.check_name}</Typography>
                          <Typography variant="caption" color="text.secondary">{config.check_type_name} · {config.attribute_name || 'table-level'}</Typography><br /><Typography variant="caption" color="text.secondary">{formatSchedule(config)}</Typography>
                        </TableCell>
                        <TableCell>{DIMENSIONS.find((d) => d.key === config.dimension_name)?.label || config.dimension_name}</TableCell>
                        <TableCell>{config.last_finished_at ? new Date(config.last_finished_at).toLocaleString() : '—'}</TableCell>
                        <TableCell>{config.last_failed_rows ?? '—'} / {config.last_failed_percent ?? '—'}%</TableCell>
                        <TableCell><Chip size="small" label={config.is_enabled ? 'Активна' : 'Отключена'} color={config.is_enabled ? 'success' : 'default'} /></TableCell>
                        <TableCell>
                          <Stack direction="row" spacing={1}>
                            <Button size="small" onClick={() => handleShowSql(config)}>SQL</Button>
                            {role === 'admin' && <Button size="small" variant="outlined" disabled={!config.is_enabled} onClick={() => handleRunCheck(config.check_config_id)}>Запуск</Button>}
                            {role === 'admin' && <Button size="small" color={config.is_enabled ? 'error' : 'success'} onClick={() => handleToggleEnabled(config)}>{config.is_enabled ? 'Отключить' : 'Включить'}</Button>}
                          </Stack>
                        </TableCell>
                      </TableRow>
                    ))}
                    {tableConfigs.length === 0 && (
                      <TableRow><TableCell colSpan={7}>Для выбранной таблицы пока нет настроенных проверок.</TableCell></TableRow>
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </>
        )}

        {selectedSql && (
          <Card elevation={0} sx={{ border: '1px solid #dbe4f0' }}>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 800 }}>SQL-запрос проверки</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {selectedSql.title}. Ниже отображается SQL последнего запуска уже с подставленными параметрами.
                  </Typography>
                </Box>
                <Stack direction="row" spacing={1}>
                  <Button variant="outlined" onClick={copySqlToClipboard}>Скопировать</Button>
                  <Button color="inherit" onClick={() => setSelectedSql(null)}>Скрыть</Button>
                </Stack>
              </Stack>
              <TextField
                fullWidth
                multiline
                minRows={10}
                value={selectedSql.sql}
                InputProps={{ readOnly: true, sx: { fontFamily: 'monospace', fontSize: 13 } }}
              />
            </CardContent>
          </Card>
        )}
      </Stack>
    )
  }

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Stack spacing={3}>
        <Box>
          <Typography variant="h3" sx={{ fontWeight: 900 }}>DQ Monitoring Service</Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>Админ-панель настройки DQ-проверок и read-only мониторинг результатов по таблицам.</Typography>
        </Box>

        <Card elevation={0} sx={{ border: '1px solid #dbe4f0' }}>
          <CardContent sx={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
            <Tabs value={tab} onChange={(_, value) => setTab(value)}>
              {role === 'admin' && <Tab value="setup" label="Настройка проверок" />}
              <Tab value="monitoring" label="Мониторинг проверок" />
            </Tabs>
            <FormControl sx={{ minWidth: 220 }}>
              <InputLabel>Роль</InputLabel>
              <Select value={role} label="Роль" onChange={(e) => { const nextRole = e.target.value; setRole(nextRole); if (nextRole !== 'admin') setTab('monitoring') }}>
                <MenuItem value="admin">Администратор</MenuItem>
                <MenuItem value="user">Обычный пользователь</MenuItem>
              </Select>
            </FormControl>
          </CardContent>
        </Card>

        {message && <Alert severity={message.type} onClose={() => setMessage(null)}>{message.text}</Alert>}
        {apiError && (
          <Alert
            severity="warning"
            action={<Button color="inherit" size="small" onClick={() => loadStatic()}>Повторить</Button>}
          >
            API недоступен: {apiError}
          </Alert>
        )}

        {dashboard && (
          <Grid container spacing={2}>
            <Grid item xs={12} md={3}><StatCard title="Активные проверки" value={dashboard.summary.active_checks} helper="Включены в конфигурации" /></Grid>
            <Grid item xs={12} md={3}><StatCard title="Неуспешные результаты" value={dashboard.summary.failed_last_run} helper="Всего по истории" /></Grid>
            <Grid item xs={12} md={3}><StatCard title="Критические проверки" value={dashboard.summary.critical_checks} helper="Severity = critical" /></Grid>
            <Grid item xs={12} md={3}><StatCard title="Всего запусков" value={dashboard.summary.total_runs} helper="Manual + scheduled" /></Grid>
          </Grid>
        )}

        {tab === 'setup' && role === 'admin' ? renderSetup() : renderMonitoring()}
      </Stack>
    </Container>
  )
}
