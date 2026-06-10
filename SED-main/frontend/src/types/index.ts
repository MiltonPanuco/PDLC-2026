// Envelope types (matches Django REST backend response format)
export interface ApiResponse<T> {
  data: T;
  meta: Record<string, unknown>;
}

export interface ApiError {
  error: {
    code: string;
    detail: string;
  };
}

// Core academic entities
export interface UnidadAcademica {
  id: number;
  nombre: string;
  clave: string;
  activa: boolean;
  created_at: string;
}

export interface ProgramaAcademico {
  id: number;
  id_unidad_academica: number;
  nombre: string;
  clave: string;
  nivel: 'lic' | 'maestria' | 'doctorado';
  activo: boolean;
  created_at: string;
}

export interface Academia {
  id: number;
  id_programa_academico: number;
  nombre: string;
  activa: boolean;
}

export interface Semestre {
  id: number;
  id_programa_academico: number;
  nombre: string; // 'I' | 'II' | ... | 'IX'
  numero: number;
  activo: boolean;
}

export interface Periodo {
  id: number;
  id_programa_academico: number;
  nombre: string; // e.g. "Agosto-Diciembre 2021"
  fecha_inicio: string;
  fecha_fin: string;
  activo: boolean;
  created_at: string;
}

export interface Grupo {
  id: number;
  id_semestre: number;
  id_periodo: number;
  nombre: string; // e.g. '1A', '2A'
  turno: 'matutino' | 'vespertino' | 'nocturno' | 'sabatino';
  activo: boolean;
}

export interface UnidadAprendizaje {
  id: number;
  id_academia: number;
  id_programa_academico: number;
  clave: string; // e.g. 'EASC300'
  nombre: string;
  activa: boolean;
}

// Users
export interface Rol {
  id: number;
  nombre: 'admin' | 'coordinador_nivel' | 'alumno_temporal' | 'director' | 'subdirector' | 'superadmin';
  descripcion: string;
}

/** Prototype-only role switcher — the subset of Rol.nombre used for mock navigation demos. */
export type MockAdminRole = 'admin' | 'director' | 'subdirector' | 'superadmin';

export interface Usuario {
  id: number;
  email: string;
  id_rol: number;
  id_programa_academico: number;
  activo: boolean;
  created_at: string;
  last_login: string | null;
}

export interface Docente {
  id: number;
  id_programa_academico: number;
  nombre: string;
  apellido_paterno: string;
  apellido_materno: string;
  email: string;
  /** Institutional employee code (e.g. "100001"). Optional for backward compat. */
  codigo_trabajador?: string;
  activo: boolean;
  created_at: string;
}

export interface UsuarioTemporal {
  id: number;
  email: string; // e.g. '5423859@tmp.uan'
  password: string;
  id_grupo: number;
  id_periodo: number;
  evaluacion_completada: boolean;
  created_at: string;
  expires_at: string;
}

// Instruments
export type Audience = 'self' | 'student' | 'admin';

export interface Instrumento {
  id: number;
  id_programa_academico: number;
  nombre: string;
  estado: 'borrador' | 'publicado';
  nivel: 'lic' | 'maestria' | 'doctorado';
  version: number;
  publicado_at: string | null;
  created_at: string;
  archivado: boolean;
  audience?: Audience;
}

export interface CategoriaPregunta {
  id: number;
  id_instrumento: number;
  nombre: string;
  orden: number;
  activa: boolean;
}

/**
 * A single conditional display rule:
 * show the question only when `id_pregunta_trigger` has answer `id_opcion_trigger`.
 */
export interface ConditionalRule {
  id_pregunta_trigger: number;
  id_opcion_trigger: number;
}

export interface Pregunta {
  id: number;
  id_categoria: number;
  id_instrumento: number;
  texto: string;
  orden: number;
  activa: boolean;
  tipo: 'cerrada' | 'abierta' | 'multiple' | 'escala';
  /** When true, an unanswered question does not block survey completion. */
  opcional?: boolean;
  /** When true, the student can leave a free-text comment for this question. */
  permite_comentario?: boolean;
  /** Conditional display rules. Empty / undefined = always show. */
  reglas_condicionales?: ConditionalRule[];
}

export interface OpcionRespuesta {
  id: number;
  id_instrumento: number;
  texto: string;
  valor: number; // 1-5 rating; 0 is opt-out/N/A and excluded from averages.
  activa: boolean;
}

export interface OpcionPregunta {
  id: number;
  id_pregunta: number;
  texto: string;
  valor: number;
  orden: number;
}

export interface CargaEvaluacion {
  id: number;
  id_semestre: number;
  id_periodo: number;
  id_grupo: number;
  id_instrumento: number;
  evaluacion_activa: boolean;
  fecha_apertura: string;
  fecha_cierre: string;
  created_at: string;
}

export interface CargaMateriaDocente {
  id: number;
  id_unidad_aprendizaje: number;
  id_docente: number;
  id_semestre: number;
  id_periodo: number;
  id_grupo: number;
  activo: boolean;
  created_at: string;
}

// Evaluation
export interface Evaluacion {
  id: number;
  id_usuario_temporal: number;
  id_carga_evaluacion: number;
  estado: 'borrador' | 'enviada';
  enviada_at: string | null;
  created_at: string;
}

export interface RespuestaEvaluacion {
  id: number;
  id_evaluacion: number;
  id_carga_materia_docente: number;
  id_pregunta: number;
  id_opcion_respuesta: number;
  valor_numerico: number; // 1-5
  /** Optional free-text comment captured when the question allows comments. */
  comentario?: string;
  created_at: string;
}

// 360 evaluation prototype
export interface Evaluacion360Package {
  id: number;
  name: string;
  periodId: number;
  targetProfessorIds: number[];
  instruments: Record<Audience, number>;
  responseOverrides?: Evaluacion360ResponseOverride[];
  created_at: string;
}

export interface Evaluacion360ResponseOverride {
  audience: Audience;
  id_docente: number;
  responseCount: number;
}

export interface Evaluacion360MateriaOption {
  id: number;
  nombre: string;
  clave: string;
}

export interface AudienceCategoryAverage {
  category: string;
  average: number;
  id_categoria?: number;
  id_instrumento?: number;
}

export interface AudienceDistributionOption {
  label: string;
  value: number;
  count: number;
  percentage: number;
  color: string;
}

export interface AudienceQuestionDistribution {
  id_pregunta?: number;
  id_categoria?: number;
  id_instrumento?: number;
  category: string;
  question: string;
  average: number;
  distribution: AudienceDistributionOption[];
}

export interface AudienceBreakdown {
  audience: Audience;
  label: string;
  responseCount: number;
  average: number;
  categoryAverages: AudienceCategoryAverage[];
  questionDistributions: AudienceQuestionDistribution[];
  comments: string[];
}

export interface Evaluacion360Report {
  periodId: number;
  periodName: string;
  materiaId: number | null;
  materiaName: string | null;
  availableMaterias: Evaluacion360MateriaOption[];
  packageId: number | null;
  packageName: string | null;
  audienceInstruments: Record<Audience, number | null>;
  professor: Pick<Docente, 'id' | 'nombre' | 'apellido_paterno' | 'apellido_materno' | 'email'>;
  overallAverage: number;
  audiences: Record<Audience, AudienceBreakdown>;
}

// ─── Prototype-only: instrument assignment overrides ──────────────────────────

/**
 * Per-docente instrument override for a specific period.
 * Stored in prototype localStorage via protoGet/protoSet('instrumento_overrides').
 */
export interface DocenteInstrumentoOverride {
  id_docente: number;
  id_periodo: number;
  id_instrumento: number;
}

// ─── Prototype-only: comparison analytics entities ───────────────────────────

/** Up to 4 periods selected for side-by-side comparison, with optional filters. */
export interface ComparisonPeriodSelection {
  /** 2–4 period IDs to compare simultaneously. */
  periodos: number[];
  /** Filter to a single docente across all selected periods. */
  id_docente?: number;
  /** Filter to a single semester across all selected periods. */
  id_semestre?: number;
}

/**
 * Maps a category/section name across periods after normalization.
 * `categoria_ids` has one entry per period in the selection; -1 means unmatched.
 */
export interface CategoryEquivalence {
  id: string;
  /** Normalized (lowercased, accent-stripped) category name used for auto-matching. */
  nombre_normalizado: string;
  categoria_ids: number[];
  resuelto: boolean;
}

/** A named comparable variable consisting of matched category equivalences. */
export interface VariableComparable {
  id: string;
  nombre: string;
  equivalencias: CategoryEquivalence[];
  /** False when the variable has at least one unmatched period and must render isolated. */
  resuelta?: boolean;
  /** When true the variable is rendered in its own isolated chart. */
  aislada: boolean;
}

/** Full comparison analytics state persisted to prototype localStorage. */
export interface ComparisonAnalyticsState {
  selection: ComparisonPeriodSelection;
  variables_comparables: VariableComparable[];
  /** IDs of variables rendered isolated rather than overlaid. */
  variables_aisladas: string[];
  updated_at: string;
}
