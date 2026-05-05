{ ============================================================================ }
{                                                                              }
{ update_library_footprints.pas                                               }
{                                                                              }
{ Replace every footprint in the focused multi-component PcbLib editor with   }
{ the same-named footprint from the other open PcbLib (house.PcbLib). Built   }
{ for the Workspace footprint refresh workflow:                                }
{                                                                              }
{   1. Open build/output/house.PcbLib in Altium (File -> Open).               }
{   2. In the Components / Explorer panel, multi-select the PCC items you     }
{      want to refresh and choose Edit. Altium opens a single                 }
{      'Footprint Library [Footprints] (N)' tab containing every selected     }
{      managed item, each with its Item Revision / Source / Revision Details  }
{      / Revision State metadata intact.                                       }
{   3. Click the Footprint Library tab so it's the focused doc.               }
{   4. Run this script: File -> Run Script -> ReplaceManagedFootprints.        }
{   5. Verify the new geometry visually, then Save (Ctrl+S) the Footprint     }
{      Library tab and right-click the project -> Save to Server. Leave       }
{      'Update items related to' enabled in the Edit Revision dialog so all   }
{      Workspace components that reference these footprints auto-bump.         }
{                                                                              }
{ Matching rule (case-insensitive):                                            }
{   For each footprint in the focused (target) library, find the footprint    }
{   with the same name in the other open PcbLib. 0 source matches or 2+       }
{   source matches both abort the run; 1 source match replaces the target's   }
{   primitives + Description/Height with the source's. The destination        }
{   footprint's Name and managed-item metadata are preserved.                 }
{                                                                              }
{ Source detection:                                                            }
{   The script scans all documents currently open in Altium and picks the     }
{   one PcbLib that is not the focused (target) document. If zero or more     }
{   than one non-target PcbLib is open, the script aborts with a clear error. }
{   No path constant to edit.                                                  }
{                                                                              }
{ ============================================================================ }


{ ----- Helpers ------------------------------------------------------------- }


{ Sanity-check entry point. Picked from File -> Run Script just to confirm    }
{ the script project is loading the latest .pas. If clicking HelloWorld in    }
{ the picker doesn't pop a dialog, the script project is stale -- close and   }
{ reopen update_library_footprints.PrjScr from the Projects panel.           }
Procedure HelloWorld;
Begin
    ShowMessage('Hello from update_library_footprints.pas v4.' + #13#10 +
                'Script project loaded the latest .pas correctly.');
End;


{ Scan all documents open in the Altium client and find every PcbLib that is  }
{ not TargetPath. Returns Nil if 0 or 2+ non-target PcbLibs are open.         }
{ On success, SourcePath is set to the found library's full path.             }
Function FindSourcePcbLib(TargetPath : String; Var SourcePath : String) : IPCB_Library;
Var
    I            : Integer;
    ServerDoc    : IServerDocument;
    DocPath      : String;
    CandCount    : Integer;
    CandPath     : String;
    Workspace    : IWorkspace;
    PrevPath     : String;
    CandDoc      : IServerDocument;
    CandLib      : IPCB_Library;
Begin
    Result    := Nil;
    SourcePath := '';
    CandCount := 0;

    { Iterate every document currently open in the Altium client. }
    For I := 0 To Client.OpenedDocumentCount - 1 Do
    Begin
        ServerDoc := Client.OpenedDocuments(I);
        If ServerDoc = Nil Then Continue;
        If UpperCase(ServerDoc.DM_DocumentKind) <> 'PCBLIB' Then Continue;
        DocPath := ServerDoc.DM_FullPath;
        If UpperCase(DocPath) = UpperCase(TargetPath) Then Continue;

        Inc(CandCount);
        CandPath := DocPath;
    End;

    If CandCount = 0 Then Exit;  { caller will emit the error }
    If CandCount > 1 Then Exit;  { caller will emit the error }

    { Briefly focus the candidate to obtain its IPCB_Library handle. }
    Workspace := GetWorkspace;
    PrevPath  := '';
    If Workspace <> Nil Then
        If Workspace.DM_FocusedDocument <> Nil Then
            PrevPath := Workspace.DM_FocusedDocument.DM_FullPath;

    CandDoc := Client.GetDocumentByPath(CandPath);
    If CandDoc = Nil Then Exit;
    Client.ShowDocument(CandDoc);
    CandLib := PCBServer.GetCurrentPCBLibrary;

    If PrevPath <> '' Then
    Begin
        ServerDoc := Client.GetDocumentByPath(PrevPath);
        If ServerDoc <> Nil Then Client.ShowDocument(ServerDoc);
    End;

    If CandLib = Nil Then Exit;
    Result     := CandLib;
    SourcePath := CandPath;
End;


{ Walk every footprint in a PcbLib via IPCB_LibraryIterator and append each   }
{ component's name (uppercased, for case-insensitive comparisons) to Names.   }
{ Returns the count.                                                           }
Function CollectFootprintNames(Lib : IPCB_Library; Names : TStringList) : Integer;
Var
    Iter : IPCB_LibraryIterator;
    Comp : IPCB_LibComponent;
Begin
    Result := 0;
    If Lib = Nil Then Exit;

    Iter := Lib.LibraryIterator_Create;
    Iter.SetState_FilterAll;
    Try
        Comp := Iter.FirstPCBObject;
        While Comp <> Nil Do
        Begin
            Names.Add(UpperCase(Comp.Name));
            Inc(Result);
            Comp := Iter.NextPCBObject;
        End;
    Finally
        Lib.LibraryIterator_Destroy(Iter);
    End;
End;


{ Count occurrences of NameUp (already uppercased) in Names.                  }
Function CountName(Names : TStringList; NameUp : String) : Integer;
Var
    I : Integer;
Begin
    Result := 0;
    For I := 0 To Names.Count - 1 Do
        If Names[I] = NameUp Then Inc(Result);
End;


{ Find a footprint by name in a PcbLib. Case-insensitive. Returns Nil if      }
{ not found. Re-iterates the library each call -- O(N) per lookup, but the    }
{ libraries we deal with are <= a few hundred footprints, so it's fine.       }
Function FindFootprint(Lib : IPCB_Library; Name : String) : IPCB_LibComponent;
Var
    Iter   : IPCB_LibraryIterator;
    Comp   : IPCB_LibComponent;
    NameUp : String;
Begin
    Result := Nil;
    If Lib = Nil Then Exit;
    NameUp := UpperCase(Name);

    Iter := Lib.LibraryIterator_Create;
    Iter.SetState_FilterAll;
    Try
        Comp := Iter.FirstPCBObject;
        While Comp <> Nil Do
        Begin
            If UpperCase(Comp.Name) = NameUp Then
            Begin
                Result := Comp;
                Break;
            End;
            Comp := Iter.NextPCBObject;
        End;
    Finally
        Lib.LibraryIterator_Destroy(Iter);
    End;
End;


{ Remove every primitive from a footprint, regardless of type. Used as the    }
{ first step of the per-target replace pass.                                   }
{                                                                              }
{ Two-phase to avoid mutating the iterator: collect first, delete second.     }
{ Comp.RemovePCBObject does the right thing for managed-item primitives.      }
Procedure ClearAllPrimitives(Comp : IPCB_LibComponent);
Var
    Iter      : IPCB_GroupIterator;
    Prim      : IPCB_Primitive;
    ToDelete  : TInterfaceList;
    I         : Integer;
Begin
    If Comp = Nil Then Exit;

    ToDelete := TInterfaceList.Create;
    Try
        Iter := Comp.GroupIterator_Create;
        Try
            Iter.AddFilter_ObjectSet(MkSet(ePadObject, eTrackObject, eArcObject,
                                           eRegionObject, eTextObject, eFillObject,
                                           eComponentBodyObject));
            Prim := Iter.FirstPCBObject;
            While Prim <> Nil Do
            Begin
                ToDelete.Add(Prim);
                Prim := Iter.NextPCBObject;
            End;
        Finally
            Comp.GroupIterator_Destroy(Iter);
        End;

        For I := 0 To ToDelete.Count - 1 Do
        Begin
            Prim := ToDelete.Items[I];
            Comp.RemovePCBObject(Prim);
        End;
    Finally
        ToDelete.Free;
    End;
End;


{ Replicate every primitive from Src into Dst. Returns the number of          }
{ primitives copied.                                                           }
{                                                                              }
{ IPCB_Primitive.Replicate makes a deep copy that's not yet owned by any      }
{ container; AddPCBObject on Dst re-parents it. This works for the full       }
{ primitive vocabulary -- pads, tracks, arcs, regions, fills, texts, AND      }
{ component bodies. The body's MODEL.NAME / Identifier travel with the        }
{ replicated body; Altium's library manager pulls the matching                }
{ Library/Models/Data entry into the destination library when needed.         }
Function ReplicatePrimitives(Src, Dst : IPCB_LibComponent) : Integer;
Var
    Iter           : IPCB_GroupIterator;
    Prim, NewPrim  : IPCB_Primitive;
    Count          : Integer;
Begin
    Count := 0;
    Result := 0;
    If Src = Nil Then Exit;
    If Dst = Nil Then Exit;

    Iter := Src.GroupIterator_Create;
    Try
        Iter.AddFilter_ObjectSet(MkSet(ePadObject, eTrackObject, eArcObject,
                                       eRegionObject, eTextObject, eFillObject,
                                       eComponentBodyObject));
        Prim := Iter.FirstPCBObject;
        While Prim <> Nil Do
        Begin
            NewPrim := Prim.Replicate;
            If NewPrim <> Nil Then
            Begin
                Dst.AddPCBObject(NewPrim);
                Inc(Count);
            End;
            Prim := Iter.NextPCBObject;
        End;
    Finally
        Src.GroupIterator_Destroy(Iter);
    End;

    Result := Count;
End;


{ Copy footprint-level Description + Height from Src to Dst. The pattern      }
{ Name is intentionally NOT copied -- the destination keeps its existing      }
{ identity (which Altium ties to the managed PCC- HRID).                      }
Procedure CopyFootprintFields(Src, Dst : IPCB_LibComponent);
Begin
    If Src = Nil Then Exit;
    If Dst = Nil Then Exit;

    If Dst.Description <> Src.Description Then
        Dst.Description := Src.Description;

    If Dst.Height <> Src.Height Then
        Dst.Height := Src.Height;
End;


{ ----- Main entry point ---------------------------------------------------- }


{ Replace every footprint in the focused multi-component PcbLib editor        }
{ with the same-named footprint from the other open PcbLib (house.PcbLib).    }
{ No-arg Procedure so Altium's Run Script picker invokes it directly without  }
{ prompting for a parameter value (parameter prompts can silently fail if      }
{ dismissed).                                                                  }
Procedure ReplaceManagedFootprints;
Var
    Workspace        : IWorkspace;
    FocusedDoc       : IDocument;
    FocusedPath      : String;
    TargetLib        : IPCB_Library;
    SourceLib        : IPCB_Library;
    SourcePath       : String;
    TargetNames      : TStringList;
    SourceNames      : TStringList;
    TargetCount      : Integer;
    SourceCount      : Integer;
    I, Dupes         : Integer;
    Tgt, Src         : IPCB_LibComponent;
    Iter             : IPCB_LibraryIterator;
    Errors           : String;
    Replaced         : Integer;
    TotalPrims       : Integer;
    PrimsThis        : Integer;
    NameUp           : String;
Begin
    { ---------------------------------------------------------------------- }
    { Diagnostic banner. If you don't see this dialog when you click          }
    { ReplaceManagedFootprints in the Run Script picker, Altium is running    }
    { a cached compilation of an older version of this file. Right-click      }
    { update_library_footprints.PrjScr in the Projects panel -> Close        }
    { Project, then File -> Open it again to force a reload. As an           }
    { independent sanity check, picking the HelloWorld procedure should       }
    { also pop a dialog -- if neither does, the script project itself is      }
    { stale and a full close + reopen of the .PrjScr (or restart of Altium   }
    { Designer) is needed.                                                    }
    { ---------------------------------------------------------------------- }
    ShowMessage('ReplaceManagedFootprints v4 starting. Click OK to continue.');

    { -------- Resolve target = focused PcbLib editor. -------------------- }
    Workspace := GetWorkspace;
    If Workspace = Nil Then
    Begin
        ShowError('GetWorkspace returned Nil. Are you running this from ' +
                  'inside Altium Designer with a Workspace connection?');
        Exit;
    End;
    If Workspace.DM_FocusedDocument = Nil Then
    Begin
        ShowError('No focused document. Multi-select PCC items in the ' +
                  'Components / Explorer panel and choose Edit, then re-run.');
        Exit;
    End;
    FocusedDoc := Workspace.DM_FocusedDocument;
    If UpperCase(FocusedDoc.DM_DocumentKind) <> 'PCBLIB' Then
    Begin
        ShowError('Focused document is not a PcbLib (kind = ' +
                  FocusedDoc.DM_DocumentKind +
                  '). Multi-select PCC items in the Components / Explorer ' +
                  'panel and choose Edit, then re-run.');
        Exit;
    End;

    FocusedPath := FocusedDoc.DM_FullPath;
    TargetLib   := PCBServer.GetCurrentPCBLibrary;
    If TargetLib = Nil Then
    Begin
        ShowError('Could not get IPCB_Library for the focused document.');
        Exit;
    End;

    { -------- Resolve source = the other open PcbLib. -------------------- }
    SourceLib := FindSourcePcbLib(FocusedPath, SourcePath);
    If SourceLib = Nil Then
    Begin
        If SourcePath = '' Then
            ShowError('Could not find a source PcbLib.' + #13#10 +
                      'Open build/output/house.PcbLib in Altium ' +
                      '(File -> Open) so exactly one non-target PcbLib is ' +
                      'open, then re-run.')
        Else
            ShowError('More than one PcbLib (other than the focused target) ' +
                      'is currently open. Close all but house.PcbLib and ' +
                      're-run.');
        Exit;
    End;

    { -------- Inventory both libraries (names only, TStringList). -------- }
    TargetNames := TStringList.Create;
    SourceNames := TStringList.Create;
    Try
        TargetCount := CollectFootprintNames(TargetLib, TargetNames);
        SourceCount := CollectFootprintNames(SourceLib, SourceNames);

        If TargetCount = 0 Then
        Begin
            ShowError('Focused library has 0 footprints. Nothing to update.');
            Exit;
        End;
        If SourceCount = 0 Then
        Begin
            ShowError(ExtractFileName(SourcePath) + ' has 0 footprints. ' +
                      'Did `python build.py house-pcblib` run successfully?');
            Exit;
        End;

        { ---------- Pre-flight: collect every name-resolution problem      }
        { before mutating anything, so we either update everything or       }
        { nothing.                                                           }
        Errors := '';

        { Target-side duplicates -- report each dupe set exactly once.      }
        For I := 0 To TargetCount - 1 Do
        Begin
            NameUp := TargetNames[I];
            Dupes := CountName(TargetNames, NameUp);
            If Dupes > 1 Then
                If TargetNames.IndexOf(NameUp) = I Then
                    Errors := Errors + #13#10 + '  - ' + NameUp +
                              ' (' + IntToStr(Dupes) +
                              ' footprints share this name in the focused library)';
        End;

        { Source coverage and source-side duplicates.                       }
        For I := 0 To TargetCount - 1 Do
        Begin
            NameUp := TargetNames[I];
            Dupes := CountName(SourceNames, NameUp);
            If Dupes = 0 Then
                Errors := Errors + #13#10 + '  - ' + NameUp +
                          ' (no match in ' +
                          ExtractFileName(SourcePath) + ')';
            If Dupes > 1 Then
                Errors := Errors + #13#10 + '  - ' + NameUp +
                          ' (' + IntToStr(Dupes) + ' source matches; ' +
                          ExtractFileName(SourcePath) +
                          ' should have unique names)';
        End;

        If Errors <> '' Then
        Begin
            ShowError('Cannot proceed -- name resolution failed:' + Errors +
                      #13#10 + #13#10 + 'No changes were made.');
            Exit;
        End;

        { ---------- Replace each target with its source counterpart. ----- }
        Replaced   := 0;
        TotalPrims := 0;
        PCBServer.PreProcess;
        Try
            { Re-iterate the target library so we have a live IPCB_LibComponent }
            { handle for each footprint -- safer than caching them across the   }
            { name-collection pass.                                              }
            Iter := TargetLib.LibraryIterator_Create;
            Iter.SetState_FilterAll;
            Try
                Tgt := Iter.FirstPCBObject;
                While Tgt <> Nil Do
                Begin
                    Src := FindFootprint(SourceLib, Tgt.Name);
                    { Pre-flight already verified non-Nil + unique. }
                    ClearAllPrimitives(Tgt);
                    PrimsThis := ReplicatePrimitives(Src, Tgt);
                    CopyFootprintFields(Src, Tgt);

                    TotalPrims := TotalPrims + PrimsThis;
                    Inc(Replaced);

                    Tgt := Iter.NextPCBObject;
                End;
            Finally
                TargetLib.LibraryIterator_Destroy(Iter);
            End;
        Finally
            PCBServer.PostProcess;
        End;

        TargetLib.Board.ViewManager_FullUpdate;
        Client.SendMessage('PCB:Zoom', 'Action=Redraw', 255, Client.CurrentView);

        ShowMessage('Replaced ' + IntToStr(Replaced) + ' footprint(s) ' +
                    '(' + IntToStr(TotalPrims) + ' primitives) from ' +
                    ExtractFileName(SourcePath) + '.' +
                    #13#10 + #13#10 +
                    'Verify visually, then Save (Ctrl+S) the Footprint ' +
                    'Library tab and right-click the project -> ' +
                    'Save to Server. Leave "Update items related to" enabled ' +
                    'in the Edit Revision dialog so all components that ' +
                    'reference these footprints auto-bump.');
    Finally
        TargetNames.Free;
        SourceNames.Free;
    End;
End;
