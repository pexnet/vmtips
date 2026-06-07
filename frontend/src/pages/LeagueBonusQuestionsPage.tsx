import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import {
  Container,
  Typography,
  Box,
  Paper,
  TextField,
  Button,
  List,
  ListItem,
  ListItemText,
  Alert,
  CircularProgress,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import { useLeagueDetail, useLeagueBonusQuestions, useCreateBonusQuestion, useUpdateBonusQuestion, useDeleteBonusQuestion, useMyBonusAnswer, useSaveBonusAnswer } from "../hooks/useLeagues";
import { isGroupOpen, usePhase } from "../hooks/usePhase";

function BonusAnswerForm({ leagueId, questionId, locked }: { leagueId: number; questionId: number; locked: boolean }) {
  const { t } = useTranslation();
  const { data: answer } = useMyBonusAnswer(leagueId, questionId);
  const saveMutation = useSaveBonusAnswer();
  const [answerText, setAnswerText] = useState("");

  useEffect(() => {
    setAnswerText(answer?.answer_text ?? "");
  }, [answer?.answer_text]);

  return (
    <Box sx={{ display: "flex", gap: 1, mt: 1 }}>
      <TextField
        size="small"
        label={t("leagues.answer")}
        value={answerText}
        onChange={(e) => setAnswerText(e.target.value)}
        disabled={locked}
        fullWidth
      />
      <Button
        variant="outlined"
        onClick={() => saveMutation.mutate({ leagueId, questionId, answerText: answerText.trim() })}
        disabled={locked || !answerText.trim()}
      >
        {t("common.save")}
      </Button>
    </Box>
  );
}

export default function LeagueBonusQuestionsPage() {
  const { t } = useTranslation();
  const { leagueId } = useParams<{ leagueId: string }>();
  const id = leagueId ? Number(leagueId) : null;

  const { data: league } = useLeagueDetail(id);
  const { data: questions = [], isLoading, error } = useLeagueBonusQuestions(id);
  const { data: phaseData } = usePhase();
  const createMutation = useCreateBonusQuestion();
  const updateMutation = useUpdateBonusQuestion();
  const deleteMutation = useDeleteBonusQuestion();

  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [newQuestion, setNewQuestion] = useState({ question_text: "", points_value: "", answer: "" });
  const [editQuestion, setEditQuestion] = useState<{ id: number; question_text: string; points_value: string; answer: string } | null>(null);

  const isAdmin = league?.is_admin ?? false;
  const answersLocked = !isGroupOpen(phaseData);

  const handleCreate = () => {
    if (!id || !newQuestion.question_text.trim() || !newQuestion.points_value) return;
    createMutation.mutate(
      {
        leagueId: id,
        payload: {
          question_text: newQuestion.question_text.trim(),
          points_value: Number(newQuestion.points_value),
          answer: newQuestion.answer.trim() || undefined,
        },
      },
      {
        onSuccess: () => {
          setCreateOpen(false);
          setNewQuestion({ question_text: "", points_value: "", answer: "" });
        },
      }
    );
  };

  const handleUpdate = () => {
    if (!id || !editQuestion) return;
    updateMutation.mutate(
      {
        leagueId: id,
        questionId: editQuestion.id,
        payload: {
          question_text: editQuestion.question_text.trim() || undefined,
          points_value: editQuestion.points_value ? Number(editQuestion.points_value) : undefined,
          answer: editQuestion.answer.trim() || undefined,
        },
      },
      {
        onSuccess: () => {
          setEditOpen(false);
          setEditQuestion(null);
        },
      }
    );
  };

  const handleDelete = (questionId: number) => {
    if (!id) return;
    if (window.confirm(t("leagues.confirm_delete_question"))) {
      deleteMutation.mutate({ leagueId: id, questionId });
    }
  };

  if (isLoading) {
    return (
      <Container sx={{ mt: 8, textAlign: "center" }}>
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Container sx={{ mt: 4, mb: 8 }}>
      <Typography variant="h4" gutterBottom>{t("leagues.bonus_questions")}</Typography>
      {league && (
        <Typography variant="subtitle1" color="text.secondary" gutterBottom>
          {league.name}
        </Typography>
      )}
      {error && <Alert severity="error" sx={{ mb: 2 }}>{t("common.error")}</Alert>}
      {!isAdmin && answersLocked && (
        <Alert severity="info" sx={{ mb: 2 }}>{t("phase.group_closed_msg")}</Alert>
      )}

      {isAdmin && (
        <Box sx={{ mb: 3 }}>
          <Button variant="contained" onClick={() => setCreateOpen(true)}>
            {t("leagues.add_question")}
          </Button>
        </Box>
      )}

      {questions.length === 0 ? (
        <Alert severity="info">{t("leagues.no_bonus_questions")}</Alert>
      ) : (
        <List>
          {questions.map((q) => (
            <Paper key={q.id} elevation={2} sx={{ mb: 2, p: 1.5 }}>
              <ListItem
                secondaryAction={
                  isAdmin ? (
                    <Box sx={{ display: "flex", gap: 1 }}>
                      <IconButton
                        size="small"
                        onClick={() => {
                          setEditQuestion({
                            id: q.id,
                            question_text: q.question_text,
                            points_value: String(q.points_value),
                            answer: q.answer || "",
                          });
                          setEditOpen(true);
                        }}
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                      <IconButton size="small" onClick={() => handleDelete(q.id)}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Box>
                  ) : null
                }
              >
                <ListItemText
                  primary={q.question_text}
                  secondary={`${t("leagues.points")}: ${q.points_value}${q.answer ? ` | ${t("leagues.answer")}: ${q.answer}` : ""}`}
                />
              </ListItem>
              {!isAdmin && id && (
                <BonusAnswerForm leagueId={id} questionId={q.id} locked={answersLocked} />
              )}
            </Paper>
          ))}
        </List>
      )}

      {/* Create dialog */}
      <Dialog open={createOpen} onClose={() => setCreateOpen(false)}>
        <DialogTitle>{t("leagues.add_question")}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label={t("leagues.question_text")}
            fullWidth
            value={newQuestion.question_text}
            onChange={(e) => setNewQuestion((p) => ({ ...p, question_text: e.target.value }))}
          />
          <TextField
            margin="dense"
            label={t("leagues.points_value")}
            type="text"
            fullWidth
            value={newQuestion.points_value}
            onChange={(e) => {
              const val = e.target.value;
              if (val === "" || /^\d*$/.test(val)) setNewQuestion((p) => ({ ...p, points_value: val }));
            }}
          />
          <TextField
            margin="dense"
            label={t("leagues.answer")}
            fullWidth
            value={newQuestion.answer}
            onChange={(e) => setNewQuestion((p) => ({ ...p, answer: e.target.value }))}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(false)}>{t("common.cancel")}</Button>
          <Button onClick={handleCreate} disabled={!newQuestion.question_text.trim() || !newQuestion.points_value}>
            {t("common.save")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit dialog */}
      <Dialog open={editOpen} onClose={() => setEditOpen(false)}>
        <DialogTitle>{t("leagues.edit_question")}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label={t("leagues.question_text")}
            fullWidth
            value={editQuestion?.question_text || ""}
            onChange={(e) => setEditQuestion((p) => p ? { ...p, question_text: e.target.value } : null)}
          />
          <TextField
            margin="dense"
            label={t("leagues.points_value")}
            type="text"
            fullWidth
            value={editQuestion?.points_value || ""}
            onChange={(e) => {
              const val = e.target.value;
              if (val === "" || /^\d*$/.test(val)) setEditQuestion((p) => p ? { ...p, points_value: val } : null);
            }}
          />
          <TextField
            margin="dense"
            label={t("leagues.answer")}
            fullWidth
            value={editQuestion?.answer || ""}
            onChange={(e) => setEditQuestion((p) => p ? { ...p, answer: e.target.value } : null)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditOpen(false)}>{t("common.cancel")}</Button>
          <Button onClick={handleUpdate} disabled={!editQuestion?.question_text.trim() || !editQuestion?.points_value}>
            {t("common.save")}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
