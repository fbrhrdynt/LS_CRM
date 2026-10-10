import {
  Ban,
  Copy,
  ExternalLink,
  Pencil,
  Plus,
  Rocket,
  Search,
  Send,
  Trash2,
} from "lucide-react";
import {
  useEffect,
  useState,
} from "react";
import { toast } from "sonner";

import api, {
  formatApiError,
} from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import EmptyState from "@/components/EmptyState";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  fmtDateTime,
} from "@/lib/format";


const EMPTY = {
  product_slug:
    "ls-amt-baroid-uae",
  version: "",
  channel: "stable",
  status: "draft",
  title: "",
  release_notes: "",
  package_url: "",
  sha256: "",
  signature: "",
  min_supported_version: "",
  mandatory: false,
  has_database_migration:
    false,
  requires_restart: true,
};

const STATUS_TONE = {
  draft:
    "bg-muted text-muted-foreground border-border",
  testing:
    "bg-warning/15 text-[hsl(var(--warning))] border-warning/40",
  published:
    "bg-success/15 text-success border-success/40",
  revoked:
    "bg-destructive/10 text-destructive border-destructive/30",
};


export default function AMTReleases() {
  const { user } = useAuth();
  const isAdmin =
    user?.role === "admin";

  const [rows, setRows] =
    useState([]);
  const [q, setQ] =
    useState("");
  const [channel, setChannel] =
    useState("all");
  const [status, setStatus] =
    useState("all");
  const [page, setPage] =
    useState(1);
  const [
    totalPages,
    setTotalPages,
  ] = useState(1);

  const [
    dialogOpen,
    setDialogOpen,
  ] = useState(false);
  const [
    editingId,
    setEditingId,
  ] = useState(null);
  const [form, setForm] =
    useState(EMPTY);
  const [busy, setBusy] =
    useState(false);

  const [
    confirmAction,
    setConfirmAction,
  ] = useState(null);

  const load = async () => {
    const params = {
      q,
      page,
      per_page: 20,
    };

    if (channel !== "all") {
      params.channel =
        channel;
    }

    if (status !== "all") {
      params.status =
        status;
    }

    const { data } =
      await api.get(
        "/amt-releases",
        { params }
      );

    setRows(
      data.items || []
    );
    setTotalPages(
      data.total_pages || 1
    );
  };

  useEffect(() => {
    load().catch((error) =>
      toast.error(
        formatApiError(error)
      )
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    q,
    channel,
    status,
    page,
  ]);

  const openNew = () => {
    setEditingId(null);
    setForm(EMPTY);
    setDialogOpen(true);
  };

  const openEdit = (row) => {
    setEditingId(row.id);
    setForm({
      ...EMPTY,
      ...row,
    });
    setDialogOpen(true);
  };

  const submit = async (
    event
  ) => {
    event.preventDefault();
    setBusy(true);

    try {
      const payload = {
        ...form,
      };

      if (editingId) {
        delete payload.status;
        delete payload.id;
        delete payload.created_at;
        delete payload.updated_at;
        delete payload.created_by;
        delete payload.published_at;
        delete payload.published_by;
        delete payload.revoked_at;
        delete payload.revoked_by;

        await api.put(
          `/amt-releases/${editingId}`,
          payload
        );
        toast.success(
          "Release updated"
        );
      } else {
        await api.post(
          "/amt-releases",
          payload
        );
        toast.success(
          "Release created"
        );
      }

      setDialogOpen(false);
      await load();
    } catch (error) {
      toast.error(
        formatApiError(error)
      );
    } finally {
      setBusy(false);
    }
  };

  const doAction =
    async () => {
      if (!confirmAction) {
        return;
      }

      const {
        type,
        row,
      } = confirmAction;

      try {
        if (
          type === "publish"
        ) {
          await api.post(
            `/amt-releases/${row.id}/publish`
          );
          toast.success(
            "Release published"
          );
        }

        if (
          type === "revoke"
        ) {
          await api.post(
            `/amt-releases/${row.id}/revoke`
          );
          toast.success(
            "Release revoked"
          );
        }

        if (
          type === "delete"
        ) {
          await api.delete(
            `/amt-releases/${row.id}`
          );
          toast.success(
            "Release deleted"
          );
        }

        setConfirmAction(null);
        await load();
      } catch (error) {
        toast.error(
          formatApiError(error)
        );
      }
    };

  const copy = async (
    value
  ) => {
    try {
      await navigator.clipboard.writeText(
        value
      );
      toast.success("Copied");
    } catch {
      toast.error(
        "Copy failed"
      );
    }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Operations"
        title="AMT Releases"
        description="Publish signed AMT release metadata used by licensed client installations."
        actions={
          isAdmin ? (
            <Button
              size="sm"
              onClick={openNew}
            >
              <Plus className="mr-2 h-4 w-4" />
              New Release
            </Button>
          ) : null
        }
      />

      <div className="mb-6 border border-primary/40 bg-primary/5 p-4">
        <div className="flex items-start gap-3">
          <Rocket className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
          <div>
            <div className="text-sm font-medium">
              Public update endpoint
            </div>
            <div className="mt-1 break-all font-mono text-xs text-muted-foreground">
              {
                process.env.REACT_APP_BACKEND_URL
              }
              /api/public/update/check
            </div>
            <div className="mt-2 text-xs text-muted-foreground">
              Only activated LogiLicense devices with the{" "}
              <code>
                update_version
              </code>{" "}
              feature receive release package metadata.
            </div>
          </div>
        </div>
      </div>

      <div className="border border-border bg-card">
        <div className="flex flex-col gap-2 border-b border-border p-3 md:flex-row">
          <div className="relative max-w-sm flex-1">
            <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={q}
              onChange={(
                event
              ) => {
                setPage(1);
                setQ(
                  event.target.value
                );
              }}
              placeholder="Search version, title, product…"
              className="pl-8"
            />
          </div>

          <Select
            value={channel}
            onValueChange={(
              value
            ) => {
              setPage(1);
              setChannel(value);
            }}
          >
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">
                All channels
              </SelectItem>
              <SelectItem value="dev">
                dev
              </SelectItem>
              <SelectItem value="beta">
                beta
              </SelectItem>
              <SelectItem value="stable">
                stable
              </SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={status}
            onValueChange={(
              value
            ) => {
              setPage(1);
              setStatus(value);
            }}
          >
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">
                All status
              </SelectItem>
              <SelectItem value="draft">
                draft
              </SelectItem>
              <SelectItem value="testing">
                testing
              </SelectItem>
              <SelectItem value="published">
                published
              </SelectItem>
              <SelectItem value="revoked">
                revoked
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        {rows.length === 0 ? (
          <EmptyState
            icon={Rocket}
            title="No AMT releases"
            action={
              isAdmin ? (
                <Button
                  size="sm"
                  onClick={openNew}
                >
                  New Release
                </Button>
              ) : null
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>
                    Version
                  </TableHead>
                  <TableHead>
                    Channel
                  </TableHead>
                  <TableHead>
                    Title
                  </TableHead>
                  <TableHead>
                    Status
                  </TableHead>
                  <TableHead>
                    Package
                  </TableHead>
                  <TableHead>
                    Published
                  </TableHead>
                  <TableHead className="text-right">
                    Actions
                  </TableHead>
                </TableRow>
              </TableHeader>

              <TableBody>
                {rows.map(
                  (row) => (
                    <TableRow
                      key={
                        row.id
                      }
                    >
                      <TableCell className="font-mono font-semibold">
                        {
                          row.version
                        }
                      </TableCell>

                      <TableCell>
                        <span className="rounded-sm border border-border bg-muted px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest">
                          {
                            row.channel
                          }
                        </span>
                      </TableCell>

                      <TableCell>
                        <div className="font-medium">
                          {
                            row.title
                          }
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {
                            row.product_slug
                          }
                        </div>
                      </TableCell>

                      <TableCell>
                        <span
                          className={`rounded-sm border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest ${
                            STATUS_TONE[
                              row.status
                            ] ||
                            ""
                          }`}
                        >
                          {
                            row.status
                          }
                        </span>
                      </TableCell>

                      <TableCell>
                        {row.package_url ? (
                          <div className="flex items-center gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              title="Copy package URL"
                              onClick={() =>
                                copy(
                                  row.package_url
                                )
                              }
                            >
                              <Copy className="h-4 w-4" />
                            </Button>

                            <Button
                              variant="ghost"
                              size="icon"
                              asChild
                              title="Open package URL"
                            >
                              <a
                                href={
                                  row.package_url
                                }
                                target="_blank"
                                rel="noreferrer"
                              >
                                <ExternalLink className="h-4 w-4" />
                              </a>
                            </Button>
                          </div>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            —
                          </span>
                        )}
                      </TableCell>

                      <TableCell className="text-xs text-muted-foreground">
                        {row.published_at
                          ? fmtDateTime(
                              row.published_at
                            )
                          : "—"}
                      </TableCell>

                      <TableCell className="whitespace-nowrap text-right">
                        {isAdmin &&
                          ![
                            "published",
                            "revoked",
                          ].includes(
                            row.status
                          ) && (
                            <Button
                              variant="ghost"
                              size="icon"
                              title="Edit release"
                              onClick={() =>
                                openEdit(
                                  row
                                )
                              }
                            >
                              <Pencil className="h-4 w-4" />
                            </Button>
                          )}

                        {isAdmin &&
                          ![
                            "published",
                            "revoked",
                          ].includes(
                            row.status
                          ) && (
                            <Button
                              variant="ghost"
                              size="icon"
                              title="Publish release"
                              onClick={() =>
                                setConfirmAction(
                                  {
                                    type:
                                      "publish",
                                    row,
                                  }
                                )
                              }
                            >
                              <Send className="h-4 w-4 text-success" />
                            </Button>
                          )}

                        {isAdmin &&
                          row.status ===
                            "published" && (
                            <Button
                              variant="ghost"
                              size="icon"
                              title="Revoke release"
                              onClick={() =>
                                setConfirmAction(
                                  {
                                    type:
                                      "revoke",
                                    row,
                                  }
                                )
                              }
                            >
                              <Ban className="h-4 w-4 text-destructive" />
                            </Button>
                          )}

                        {isAdmin &&
                          ![
                            "published",
                            "revoked",
                          ].includes(
                            row.status
                          ) && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="text-destructive"
                              title="Delete release"
                              onClick={() =>
                                setConfirmAction(
                                  {
                                    type:
                                      "delete",
                                    row,
                                  }
                                )
                              }
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          )}
                      </TableCell>
                    </TableRow>
                  )
                )}
              </TableBody>
            </Table>
          </div>
        )}

        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-border p-3 text-sm">
            <div className="text-muted-foreground">
              Page {page} of{" "}
              {totalPages}
            </div>

            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={
                  page <= 1
                }
                onClick={() =>
                  setPage(
                    (current) =>
                      current -
                      1
                  )
                }
              >
                Prev
              </Button>

              <Button
                variant="outline"
                size="sm"
                disabled={
                  page >=
                  totalPages
                }
                onClick={() =>
                  setPage(
                    (current) =>
                      current +
                      1
                  )
                }
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>

      <Dialog
        open={dialogOpen}
        onOpenChange={
          setDialogOpen
        }
      >
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-[760px]">
          <DialogHeader>
            <DialogTitle>
              {editingId
                ? "Edit AMT Release"
                : "New AMT Release"}
            </DialogTitle>
          </DialogHeader>

          <form
            onSubmit={submit}
            className="grid grid-cols-1 gap-4 md:grid-cols-2"
          >
            <Field
              label="Product Slug *"
            >
              <Input
                required
                value={
                  form.product_slug
                }
                onChange={(
                  event
                ) =>
                  setForm({
                    ...form,
                    product_slug:
                      event.target
                        .value,
                  })
                }
              />
            </Field>

            <Field label="Version *">
              <Input
                required
                value={
                  form.version
                }
                onChange={(
                  event
                ) =>
                  setForm({
                    ...form,
                    version:
                      event.target
                        .value,
                  })
                }
                placeholder="1.2.0"
              />
            </Field>

            <Field label="Channel">
              <Select
                value={
                  form.channel
                }
                onValueChange={(
                  value
                ) =>
                  setForm({
                    ...form,
                    channel:
                      value,
                  })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="dev">
                    dev
                  </SelectItem>
                  <SelectItem value="beta">
                    beta
                  </SelectItem>
                  <SelectItem value="stable">
                    stable
                  </SelectItem>
                </SelectContent>
              </Select>
            </Field>

            {!editingId && (
              <Field label="Initial Status">
                <Select
                  value={
                    form.status
                  }
                  onValueChange={(
                    value
                  ) =>
                    setForm({
                      ...form,
                      status:
                        value,
                    })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="draft">
                      draft
                    </SelectItem>
                    <SelectItem value="testing">
                      testing
                    </SelectItem>
                  </SelectContent>
                </Select>
              </Field>
            )}

            <Field
              label="Title *"
              span
            >
              <Input
                required
                value={
                  form.title
                }
                onChange={(
                  event
                ) =>
                  setForm({
                    ...form,
                    title:
                      event.target
                        .value,
                  })
                }
                placeholder="AMT 1.2.0"
              />
            </Field>

            <Field
              label="Release Notes"
              span
            >
              <Textarea
                rows={5}
                value={
                  form.release_notes
                }
                onChange={(
                  event
                ) =>
                  setForm({
                    ...form,
                    release_notes:
                      event.target
                        .value,
                  })
                }
                placeholder="- Calibration export&#10;- License update&#10;- Security fixes"
              />
            </Field>

            <Field
              label="Package URL"
              span
            >
              <Input
                value={
                  form.package_url
                }
                onChange={(
                  event
                ) =>
                  setForm({
                    ...form,
                    package_url:
                      event.target
                        .value,
                  })
                }
                placeholder="https://release.logisourcedigital.web.id/releases/1.2.0/amt-1.2.0.tar.gz"
              />
            </Field>

            <Field
              label="SHA256"
              span
            >
              <Input
                value={
                  form.sha256
                }
                onChange={(
                  event
                ) =>
                  setForm({
                    ...form,
                    sha256:
                      event.target
                        .value,
                  })
                }
                className="font-mono"
                placeholder="64 hexadecimal characters"
              />
            </Field>

            <Field
              label="Signature"
              span
            >
              <Textarea
                rows={3}
                value={
                  form.signature
                }
                onChange={(
                  event
                ) =>
                  setForm({
                    ...form,
                    signature:
                      event.target
                        .value,
                  })
                }
                className="font-mono text-xs"
                placeholder="Base64 or armored detached signature"
              />
            </Field>

            <Field label="Minimum Supported Version">
              <Input
                value={
                  form.min_supported_version
                }
                onChange={(
                  event
                ) =>
                  setForm({
                    ...form,
                    min_supported_version:
                      event.target
                        .value,
                  })
                }
                placeholder="1.0.0"
              />
            </Field>

            <div className="space-y-2">
              <Label>
                Release Behavior
              </Label>

              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={
                    form.mandatory
                  }
                  onChange={(
                    event
                  ) =>
                    setForm({
                      ...form,
                      mandatory:
                        event.target
                          .checked,
                    })
                  }
                />
                Mandatory update
              </label>

              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={
                    form.has_database_migration
                  }
                  onChange={(
                    event
                  ) =>
                    setForm({
                      ...form,
                      has_database_migration:
                        event.target
                          .checked,
                    })
                  }
                />
                Has database migration
              </label>

              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={
                    form.requires_restart
                  }
                  onChange={(
                    event
                  ) =>
                    setForm({
                      ...form,
                      requires_restart:
                        event.target
                          .checked,
                    })
                  }
                />
                Requires restart
              </label>
            </div>

            <DialogFooter className="md:col-span-2">
              <Button
                type="button"
                variant="outline"
                onClick={() =>
                  setDialogOpen(
                    false
                  )
                }
              >
                Cancel
              </Button>

              <Button
                type="submit"
                disabled={busy}
              >
                {busy
                  ? "Saving..."
                  : "Save Release"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog
        open={Boolean(
          confirmAction
        )}
        onOpenChange={(
          open
        ) => {
          if (!open) {
            setConfirmAction(
              null
            );
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {confirmAction?.type ===
              "publish"
                ? "Publish release?"
                : confirmAction?.type ===
                    "revoke"
                  ? "Revoke release?"
                  : "Delete release?"}
            </AlertDialogTitle>

            <AlertDialogDescription>
              {confirmAction?.type ===
              "publish"
                ? "Published release metadata becomes available to entitled AMT clients."
                : confirmAction?.type ===
                    "revoke"
                  ? "Revoked releases stop being offered to AMT clients."
                  : "Delete this draft/testing release?"}
            </AlertDialogDescription>
          </AlertDialogHeader>

          <AlertDialogFooter>
            <AlertDialogCancel>
              Cancel
            </AlertDialogCancel>

            <AlertDialogAction
              onClick={
                doAction
              }
              className={
                confirmAction?.type ===
                  "publish"
                  ? ""
                  : "bg-destructive text-destructive-foreground hover:bg-destructive/90"
              }
            >
              Confirm
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}


function Field({
  label,
  span = false,
  children,
}) {
  return (
    <div
      className={`space-y-1.5 ${
        span
          ? "md:col-span-2"
          : ""
      }`}
    >
      <Label className="text-xs uppercase tracking-widest">
        {label}
      </Label>
      {children}
    </div>
  );
}
